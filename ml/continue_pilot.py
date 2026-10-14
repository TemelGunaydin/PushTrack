"""Continue the existing candidate manifest using the official CodeT5 tokenizer."""

import argparse
from collections import Counter
import datetime as dt
import importlib.metadata
import json
import os
from pathlib import Path
import re
import shutil
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.parse import quote

from compare_tokenizers import CANDIDATES, verify_asset
from prepare_pilot import Network, PREFIX, Reject, SECRET, digest, json_write, jsonl_write, verify_row


def read_rows(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


class OfficialTokenizer:
    """Only an interface adapter; all token IDs come from Transformers itself."""

    def __init__(self, directory):
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
        from transformers import AddedToken, RobertaTokenizer

        for name, (size, blob) in CANDIDATES["codet5-small"]["files"].items():
            verify_asset((directory / name).read_bytes(), size, blob)
        special = json.loads((directory / "special_tokens_map.json").read_text())
        # Legacy descriptors lack the __type tag expected by Transformers 5.
        # Preserve every original flag and ID; never modify the asset files.
        kwargs = {name: [AddedToken(**item) for item in value] if isinstance(value, list)
                  else AddedToken(**value) for name, value in special.items()}
        self.tokenizer = RobertaTokenizer.from_pretrained(
            str(directory), local_files_only=True, clean_up_tokenization_spaces=False, **kwargs
        )
        assert (len(self.tokenizer), self.tokenizer.bos_token_id, self.tokenizer.eos_token_id) == (32100, 1, 2)

    def encode(self, text):
        if any(marker in text for marker in self.tokenizer.all_special_tokens):
            raise Reject("literal_special_marker")
        raw = self.tokenizer.encode(text, add_special_tokens=False, truncation=False)
        if self.tokenizer.unk_token_id in raw:
            raise Reject("unknown_token")
        decoded = self.tokenizer.decode(raw, skip_special_tokens=False, clean_up_tokenization_spaces=False)
        if decoded != text:
            raise Reject("tokenizer_not_lossless")
        return SimpleNamespace(ids=self.tokenizer.encode(text, add_special_tokens=True, truncation=False))


def choose_candidates(candidates, prior_rows, rejections):
    """Resume completed identities, except length rejects under the old tokenizer."""
    key = lambda row: (row["repo_id"].casefold(), row["commit_id"])
    completed = {key(row) for row in prior_rows}
    completed.update(key(row) for row in rejections if row["reason"] != "token_budget")
    train = iter(row for row in candidates if row["split"] == "train" and key(row) not in completed)
    validation = iter(row for row in candidates if row["split"] == "validation" and key(row) not in completed)
    result = []
    while len(result) < 40:
        batch = [next(train, None), next(train, None), next(train, None), next(validation, None)]
        if not any(batch):
            break
        result.extend(row for row in batch if row is not None)
    return result[:40]


def screen_source_files(network, row, directory):
    """Retain original changed-file bytes; flag obvious conflicting notices/secrets.

    This is a conservative screening check, not exhaustive legal clearance of
    nested licensing, provenance chains, or every third-party code fragment.
    """
    evidence = []
    for path in row["files"]:
        url = f'https://raw.githubusercontent.com/{row["repo_id"]}/{row["commit_id"]}/{quote(path, safe="/")}'
        content, _ = network.fetch(url, 200_000)
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError as error:
            raise Reject("source_file_encoding") from error
        if SECRET.search(text):
            raise Reject("source_possible_secret")
        declarations = re.findall(r"SPDX-License-Identifier:\s*([^\n\r]+)", text)
        if any(value.strip(" */\t") != "MIT" for value in declarations):
            raise Reject("source_non_MIT_declaration")
        if re.search(r"GNU (?:Lesser |Affero )?General Public License|Apache License|Mozilla Public License", text, re.I):
            raise Reject("source_conflicting_notice")
        sha = digest(content)
        (directory / (sha + ".txt")).write_bytes(content)
        evidence.append({"path": path, "revision": row["commit_id"], "url": url, "sha256": sha})
    row["source_file_screening"] = evidence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pilot", type=Path, required=True)
    parser.add_argument("--tokenizer", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; preserve previous evidence")
    candidates = read_rows(args.pilot / "candidates.jsonl")
    prior = read_rows(args.pilot / "review-pending.jsonl")
    rejected_before = read_rows(args.pilot / "rejections.jsonl")
    reviews = {row["commit_id"]: row for row in read_rows(args.pilot / "assistant-review.jsonl")}
    tokenizer = OfficialTokenizer(args.tokenizer)
    args.output.mkdir(parents=True)
    for name in ("licenses", "source-files", "provenance"):
        (args.output / name).mkdir()
    for name in ("continue_pilot.py", "prepare_pilot.py", "compare_tokenizers.py", "requirements-data.lock"):
        shutil.copyfile(Path(__file__).parent / name, args.output / "provenance" / name)
    report = {"started_at_utc": dt.datetime.now(dt.UTC).isoformat(), "status": "running",
              "source_manifest_sha256": digest((args.pilot / "candidates.jsonl").read_bytes()),
              "tokenizer_repo": CANDIDATES["codet5-small"]["repo"],
              "tokenizer_revision": CANDIDATES["codet5-small"]["revision"],
              "transformers": importlib.metadata.version("transformers"),
              "purpose": "small local research pilot, not product distribution",
              "shards_downloaded": 0, "model_weights_downloaded": False, "training_approved": 0}
    pending, rejections = [], []
    network = Network(budget=20_000_000)
    seen_diffs = set()
    # Keep earlier holds visible for explicit relabel/reject decisions; none is approved here.
    work = [(row, True) for row in prior]
    work += [(row, False) for row in choose_candidates(candidates, prior, rejected_before)]
    try:
        for candidate, reused in work:
            print(f'Checking {candidate["repo_id"]} ({"reuse" if reused else "new"})', flush=True)
            try:
                if reused:
                    row = dict(candidate)
                    if digest(row["diff"].encode()) != row["diff_sha256"]:
                        raise Reject("prior_diff_integrity")
                    row["input_tokens"] = len(tokenizer.encode(PREFIX + row["diff"]).ids)
                    row["target_tokens"] = len(tokenizer.encode(row["message"]).ids)
                    if row["input_tokens"] > 512 or row["target_tokens"] > 64:
                        raise Reject("token_budget")
                    name = row["source"]["license_sha256"] + ".txt"
                    notice = (args.pilot / "licenses" / name).read_bytes()
                    if digest(notice) != row["source"]["license_sha256"]:
                        raise Reject("prior_notice_integrity")
                    (args.output / "licenses" / name).write_bytes(notice)
                    row["prior_assistant_review"] = reviews[row["commit_id"]]
                else:
                    row = verify_row(network, candidate, tokenizer, args.output / "licenses")
                if row["diff_sha256"] in seen_diffs:
                    raise Reject("duplicate_diff")
                screen_source_files(network, row, args.output / "source-files")
                seen_diffs.add(row["diff_sha256"])
                pending.append(row)
            except Reject as error:
                rejections.append({"repo_id": candidate["repo_id"], "commit_id": candidate["commit_id"], "reason": str(error)})
            except HTTPError as error:
                rejections.append({"repo_id": candidate["repo_id"], "commit_id": candidate["commit_id"], "reason": f"http_{error.code}"})
            if len(pending) >= 30:
                break
        report["status"] = "complete_bounded_pass"
    except Exception as error:
        report["status"] = "stopped"
        report["stop_reason"] = f"{type(error).__name__}: {error}"
    finally:
        jsonl_write(args.output / "review-pending.jsonl", pending)
        jsonl_write(args.output / "rejections.jsonl", rejections)
        report.update({"finished_at_utc": dt.datetime.now(dt.UTC).isoformat(), "pending_review": len(pending),
                       "pending_by_split": dict(Counter(row["split"] for row in pending)),
                       "rejections": dict(Counter(row["reason"] for row in rejections)),
                       "github_api_requests": network.github_requests, "github_api_remaining": network.remaining,
                       "response_body_bytes": network.received})
        json_write(args.output / "report.json", report)
        print(json.dumps(report, indent=2))
    return 0 if report["status"] == "complete_bounded_pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
