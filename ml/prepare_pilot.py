"""Bounded, review-only CommitChronicle pilot. Never trains or executes source code."""

from __future__ import annotations

import argparse
import base64
from collections import Counter, defaultdict, deque
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import time
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

DATASET = "JetBrains-Research/commit-chronicle"
REVISION = "5fd076e67b812a9f3d1999e5e40f71715f84bb51"
TOKENIZER_REVISION = "df1b051c49625cf57a3d0d8d3863ed4d13564fe4"
TOKENIZER_HASH = "d2acde0d8d71dd30a711834b07781b9c89feaac33fd332f60507699282740066"
SHARDS = {
    "train": (
        "train-00000-of-00061-2a7ccc8e843f5f5b.parquet", 179224070,
        "436753ecfbd4402c3d7b3150f3a9b17c0b4041c79964ac19a47e0f9fd7913322",
    ),
    "validation": (
        "validation-00000-of-00012-8c21a992ac7a2944.parquet", 153306487,
        "fb62e799f6e0d552d8d654b3c7e73bcb3cb54c83dafb0f149edf45ebdbd6dafc",
    ),
}
PREFIX = "summarize changes: "
REPO = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")
SHA = re.compile(r"[0-9a-f]{40}\Z")
PATH = re.compile(r"[A-Za-z0-9_./-]+\Z")
SECRET = re.compile(
    r"-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----|\bAKIA[0-9A-Z]{16}\b|"
    r"\bgh[pousr]_[A-Za-z0-9]{20,}\b|\bgithub_pat_[A-Za-z0-9_]{20,}\b|"
    r"(?i:(?:password|api[_-]?key|secret|access[_-]?token)\s*[:=]\s*[\"'][^\"'\n]{8,}[\"'])"
)
HUNK = re.compile(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(?:.*)\Z")


class Reject(ValueError):
    """A conservative data-policy rejection, not an infrastructure error."""


class StopCollection(RuntimeError):
    """A hard network/rate limit; never bypass or retry around it."""


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def json_write(path: Path, obj: object) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def jsonl_write(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=True) + "\n")


class Network:
    """Only public HTTPS endpoints; no credentials, remote scripts, or silent retries."""

    def __init__(self, budget: int = 400_000_000):
        self.budget = budget
        self.received = 0
        self.requests = 0
        self.github_requests = 0
        self.remaining: int | None = None

    def fetch(self, url: str, limit: int, destination: Path | None = None) -> tuple[bytes, dict]:
        is_api = url.startswith("https://api.github.com/")
        if is_api:
            if self.github_requests >= 54 or (self.remaining is not None and self.remaining <= 5):
                raise StopCollection("GitHub API budget reached; wait for reset before another approved run")
            self.github_requests += 1
        if "github.com/" in url or "githubusercontent.com/" in url:
            time.sleep(1)
        headers = {"User-Agent": "PushTrack-data-pilot/0.1", "Accept": "application/json"}
        self.requests += 1
        try:
            response = urlopen(Request(url, headers=headers), timeout=45)
        except HTTPError as error:
            if error.code in (403, 429):
                raise StopCollection(f"HTTP {error.code}: access or rate limit; stopping") from error
            raise
        with response:
            if not response.url.startswith("https://"):
                raise StopCollection("Refusing a non-HTTPS redirect")
            response_headers = dict(response.headers.items())
            remaining = response.headers.get("X-RateLimit-Remaining")
            if is_api and remaining is not None:
                self.remaining = int(remaining)
            length = int(response.headers.get("Content-Length", "0"))
            if length > limit:
                raise Reject("response_too_large")
            if self.received + length > self.budget:
                raise StopCollection("Network byte budget reached")
            data = bytearray()
            total = 0
            partial = destination.with_suffix(destination.suffix + ".part") if destination else None
            file = partial.open("wb") if partial else None
            try:
                while block := response.read(min(1024 * 1024, limit - total + 1)):
                    total += len(block)
                    self.received += len(block)
                    if total > limit:
                        raise Reject("response_too_large")
                    if self.received > self.budget:
                        raise StopCollection("Network byte budget reached")
                    if file:
                        file.write(block)
                    else:
                        data.extend(block)
            finally:
                if file:
                    file.close()
            if destination and partial:
                partial.replace(destination)
            return bytes(data), response_headers

    def json(self, url: str, limit: int = 2_000_000) -> tuple[object, dict]:
        data, headers = self.fetch(url, limit)
        return json.loads(data), headers


def pinned_download(network: Network, path: Path, url: str, size: int, sha: str) -> None:
    if not path.exists():
        print(f"Downloading {path.name}: at most {size:,} bytes", flush=True)
        network.fetch(url, size, path)
    with path.open("rb") as file:
        actual = hashlib.file_digest(file, "sha256").hexdigest()
    if path.stat().st_size != size or actual != sha:
        raise StopCollection(f"Pinned integrity check failed: {path.name}; do not use or silently replace it")


def identity(repo: str, commit: str) -> None:
    if not REPO.fullmatch(repo) or not SHA.fullmatch(commit):
        raise Reject("invalid_identity")
    if any(part in (".", "..") for part in repo.split("/")):
        raise Reject("invalid_identity")


def safe_path(path: str) -> bool:
    return bool(PATH.fullmatch(path)) and not path.startswith("/") and all(
        part not in ("", ".", "..") for part in path.split("/")
    )


def subject(message: str) -> str:
    if not isinstance(message, str) or not message.strip():
        raise Reject("empty_subject")
    text = message.splitlines()[0].strip()
    if not 10 <= len(text) <= 72 or len(text.split()) < 3:
        raise Reject("subject_length")
    if not text.isascii() or any(ord(c) < 32 or ord(c) == 127 for c in text):
        raise Reject("subject_characters")
    if re.match(r"(?i)^(merge|revert|wip|bump|release)\b", text):
        raise Reject("subject_policy")
    if re.search(r"https?://|\b\S+@\S+\.\S+\b|#\d+", text) or SECRET.search(text):
        raise Reject("subject_reference_or_secret")
    return text  # ASCII is not proof of English; human review remains mandatory.


def check_hunks(section: str) -> tuple[int, int]:
    """Validate declared old/new line counts and report added/deleted lines."""
    old_left = new_left = 0
    additions = deletions = 0
    seen_hunk = False
    for line in section.split("\n"):
        match = HUNK.fullmatch(line)
        if match:
            if old_left or new_left:
                raise Reject("incomplete_hunk")
            old_left = int(match[2]) if match[2] is not None else 1
            new_left = int(match[4]) if match[4] is not None else 1
            seen_hunk = True
        elif seen_hunk:
            if line == "\\ No newline at end of file":
                continue
            if line == "":
                if old_left or new_left:
                    raise Reject("incomplete_hunk")
                continue
            if line.startswith(" "):
                old_left -= 1
                new_left -= 1
            elif line.startswith("+"):
                new_left -= 1
                additions += 1
            elif line.startswith("-"):
                old_left -= 1
                deletions += 1
            else:
                raise Reject("unsupported_hunk_line")
            if old_left < 0 or new_left < 0:
                raise Reject("hunk_count_mismatch")
    if not seen_hunk or old_left or new_left:
        raise Reject("missing_or_incomplete_hunk")
    return additions, deletions


def validate_diff(diff: str, commit: dict) -> None:
    """Require a complete small text diff matching independent GitHub file metadata."""
    files = commit.get("files", [])
    if not 1 <= len(files) <= 5:
        raise Reject("file_count")
    if any(marker in diff for marker in ("GIT binary patch", "Binary files ", "Subproject commit ", "\x00")):
        raise Reject("binary_or_submodule")
    if SECRET.search(diff):
        raise Reject("possible_secret")
    if any(ord(c) < 32 and c not in "\n\r\t" for c in diff) or "\x7f" in diff:
        raise Reject("diff_control_characters")
    sections = re.split(r"(?m)(?=^diff --git )", diff)
    if sections[0] != "" or len(sections) - 1 != len(files):
        raise Reject("diff_file_count_mismatch")
    by_path = {file["filename"]: file for file in files}
    if len(by_path) != len(files):
        raise Reject("duplicate_path")
    added = deleted = 0
    for section in sections[1:]:
        header = section.split("\n", 1)[0]
        match = re.fullmatch(r"diff --git a/(\S+) b/(\S+)", header)
        if not match or match[1] != match[2] or not safe_path(match[2]):
            raise Reject("unsupported_path_or_rename")
        path = match[2]
        file = by_path.pop(path, None)
        if file is None or file.get("status") not in ("modified", "added", "removed"):
            raise Reject("unsupported_file_status")
        if re.search(r"(?i)(^|/)(vendor|node_modules|dist|build|\.git)/|(^|/)(package-lock\.json|yarn\.lock|Cargo\.lock)$|\.(min\.js|svg|ipynb)$", path):
            raise Reject("generated_or_vendor_path")
        if re.search(r"(?im)^[+ -].*(auto.?generated|do not edit)", section):
            raise Reject("generated_content")
        a, d = check_hunks(section)
        if a != file.get("additions") or d != file.get("deletions"):
            raise Reject("diff_stats_mismatch")
        added += a
        deleted += d
    if by_path or added != commit.get("stats", {}).get("additions") or deleted != commit.get("stats", {}).get("deletions"):
        raise Reject("commit_stats_mismatch")


def candidates(directory: Path) -> tuple[list[dict], dict]:
    import pyarrow.parquet as pq

    all_rows: list[dict] = []
    counts: dict = {}
    train_repos: set[str] = set()
    seen: set[tuple[str, str]] = set()
    for split, cap in (("train", 1000), ("validation", 200)):
        per_repo: Counter = Counter()
        rejected: Counter = Counter()
        scanned = 0
        selected = []
        file = directory / SHARDS[split][0]
        for batch in pq.ParquetFile(file).iter_batches(batch_size=128, columns=["repo", "hash", "license", "message", "mods"]):
            for row in batch.to_pylist():
                scanned += 1
                try:
                    repo, sha = row["repo"], row["hash"]
                    identity(repo, sha)
                    repo_key = repo.casefold()
                    if row["license"] != "MIT License":
                        raise Reject("source_license_label")
                    subject(row["message"])
                    if not 1 <= len(row["mods"]) <= 5:
                        raise Reject("processed_file_count")
                    if sum(len(m.get("diff") or "") for m in row["mods"]) > 1800:
                        raise Reject("processed_diff_characters")
                    if per_repo[repo_key] >= 20:
                        raise Reject("per_repository_cap")
                    if (repo_key, sha) in seen or (split == "validation" and repo_key in train_repos):
                        raise Reject("duplicate_or_split_overlap")
                    seen.add((repo_key, sha))
                    per_repo[repo_key] += 1
                    selected.append({"repo_id": repo, "commit_id": sha, "split": split})
                except Reject as error:
                    rejected[str(error)] += 1
                if len(selected) >= cap:
                    break
            if len(selected) >= cap:
                break
        # Spread verification attempts across repositories rather than one contiguous project.
        groups: dict[str, deque] = defaultdict(deque)
        for row in selected:
            groups[row["repo_id"]].append(row)
        while any(groups.values()):
            for repo in sorted(groups):
                if groups[repo]:
                    all_rows.append(groups[repo].popleft())
        if split == "train":
            train_repos.update(per_repo)
        counts[split] = {"scanned": scanned, "selected": len(selected), "repositories": len(per_repo), "rejections": dict(rejected)}
    return all_rows, counts


def verify_row(network: Network, candidate: dict, tokenizer, licenses: Path) -> dict:
    repo, sha = candidate["repo_id"], candidate["commit_id"]
    identity(repo, sha)
    info, headers = network.json(f"https://api.github.com/repos/{repo}/commits/{sha}?per_page=100")
    if any(key.lower() == "link" and 'rel="next"' in value for key, value in headers.items()):
        raise Reject("paginated_commit")
    if info.get("sha") != sha or len(info.get("parents", [])) != 1:
        raise Reject("identity_or_parent_count")
    message = subject(info["commit"]["message"])
    if not 1 <= len(info.get("files", [])) <= 5:
        raise Reject("file_count")
    patch_url = f"https://github.com/{repo}/commit/{sha}.diff"
    patch, _ = network.fetch(patch_url, 100_000)
    try:
        diff = patch.decode("utf-8")
    except UnicodeDecodeError as error:
        raise Reject("diff_encoding") from error
    validate_diff(diff, info)
    input_tokens = len(tokenizer.encode(PREFIX + diff).ids)
    target_tokens = len(tokenizer.encode(message).ids)
    if input_tokens > 512 or target_tokens > 64:
        raise Reject("token_budget")
    # Exact original revision, not the repository's current default-branch license.
    license_info, _ = network.json(f"https://api.github.com/repos/{repo}/license?ref={quote(sha)}", 150_000)
    if license_info.get("license", {}).get("spdx_id") != "MIT" or license_info.get("encoding") != "base64":
        raise Reject("unverified_MIT_license")
    try:
        notice = base64.b64decode(license_info["content"], validate=False)
        notice_text = notice.decode("utf-8")
    except (ValueError, UnicodeDecodeError) as error:
        raise Reject("license_encoding") from error
    if "Permission is hereby granted, free of charge" not in notice_text or "THE SOFTWARE IS PROVIDED" not in notice_text:
        raise Reject("license_text_mismatch")
    blob_sha = hashlib.sha1(b"blob " + str(len(notice)).encode() + b"\0" + notice).hexdigest()
    if blob_sha != license_info.get("sha"):
        raise Reject("license_blob_mismatch")
    notice_hash = digest(notice)
    (licenses / (notice_hash + ".txt")).write_bytes(notice)
    return {
        "schema_version": 1, **candidate,
        "parent_id": info["parents"][0]["sha"],
        "source": {"kind": "git", "url": f"https://github.com/{repo}/commit/{sha}", "license": "MIT",
                   "license_path": license_info["path"], "license_blob_sha": license_info["sha"],
                   "license_sha256": notice_hash},
        "dataset": {"name": DATASET, "revision": REVISION, "shard": SHARDS[candidate["split"]][0]},
        "diff": diff, "diff_sha256": digest(patch), "message": message,
        "files": [f["filename"] for f in info["files"]],
        "input_tokens": input_tokens, "target_tokens": target_tokens,
        "review_status": "pending",
        "review_requirements": ["English", "faithful subject", "secrets and personal data", "per-file licenses and notices", "fork-family and near-duplicate separation"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path, help="New local data directory; never overwritten.")
    parser.add_argument("--verify-limit", type=int, default=24, choices=range(1, 25), metavar="1..24")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists. Preserve it as evidence; choose a new directory only for an approved rerun.")
    args.output.mkdir(parents=True)
    licenses = args.output / "licenses"
    licenses.mkdir()
    network = Network()
    report: dict = {"started_at_utc": dt.datetime.now(dt.UTC).isoformat(), "dataset_revision": REVISION,
                   "tokenizer_revision": TOKENIZER_REVISION, "input_prefix": PREFIX,
                   "collector_sha256": digest(Path(__file__).read_bytes()),
                   "status": "running", "training_ready": 0, "accepted": 0,
                   "sampling": "bounded first train/validation shards; deterministic, not representative"}
    pending: list[dict] = []
    rejected: list[dict] = []
    try:
        from tokenizers import Tokenizer

        for name, size, sha in SHARDS.values():
            pinned_download(network, args.output / name,
                            f"https://huggingface.co/datasets/{DATASET}/resolve/{REVISION}/data/{name}", size, sha)
        tokenizer_path = args.output / "tokenizer.json"
        pinned_download(network, tokenizer_path,
                        f"https://huggingface.co/google-t5/t5-small/resolve/{TOKENIZER_REVISION}/tokenizer.json",
                        1389353, TOKENIZER_HASH)
        tokenizer = Tokenizer.from_file(str(tokenizer_path))
        tokenizer.no_padding()
        tokenizer.no_truncation()
        rows, counts = candidates(args.output)
        jsonl_write(args.output / "candidates.jsonl", rows)
        report["candidates"] = counts
        # Reserve one quarter of attempts for validation without touching any test split.
        val_limit = max(1, args.verify_limit // 4)
        chosen = [r for r in rows if r["split"] == "train"][:args.verify_limit - val_limit]
        chosen += [r for r in rows if r["split"] == "validation"][:val_limit]
        seen_diffs: set[str] = set()
        for index, candidate in enumerate(chosen, 1):
            print(f"Verifying original commit {index}/{len(chosen)}", flush=True)
            try:
                row = verify_row(network, candidate, tokenizer, licenses)
                if row["diff_sha256"] in seen_diffs:
                    raise Reject("duplicate_original_diff")
                seen_diffs.add(row["diff_sha256"])
                pending.append(row)
            except Reject as error:
                rejected.append({**candidate, "reason": str(error)})
            except HTTPError as error:
                rejected.append({**candidate, "reason": f"http_{error.code}"})
        report["status"] = "complete_bounded_run"
    except Exception as error:
        report["status"] = "stopped"
        report["stop_reason"] = f"{type(error).__name__}: {error}"
    finally:
        jsonl_write(args.output / "review-pending.jsonl", pending)
        jsonl_write(args.output / "rejections.jsonl", rejected)
        report.update({"finished_at_utc": dt.datetime.now(dt.UTC).isoformat(),
                       "pending_review": len(pending), "verification_rejections": dict(Counter(r["reason"] for r in rejected)),
                       "network_received_bytes": network.received, "network_requests": network.requests,
                       "github_api_requests": network.github_requests, "github_api_remaining": network.remaining,
                       "pending_by_split": dict(Counter(r["split"] for r in pending)),
                       "pending_multi_file": sum(len(r["files"]) > 1 for r in pending)})
        json_write(args.output / "report.json", report)
        print(json.dumps(report, indent=2), flush=True)
    return 0 if report["status"] == "complete_bounded_run" else 1


if __name__ == "__main__":
    raise SystemExit(main())
