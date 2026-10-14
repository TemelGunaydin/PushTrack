"""Stream the full pinned corpus into filtered candidates, not falsely verified diffs."""

import argparse
from collections import Counter
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import sqlite3

from continue_pilot import OfficialTokenizer
from download_corpus import EXPECTED_ROWS, selected_shards
from prepare_pilot import DATASET, REVISION, PREFIX, SECRET, Reject, identity, safe_path, subject, json_write

ACTIONS = set("add added adds fix fixed fixes update updated updates remove removed removes correct corrected improve improved allow avoid use handle prevent ensure support make move rename replace refactor document enable disable implement stop start expose restore skip clean simplify optimize respect preserve resolve include exclude change check return set unset ignore handle extend reduce increase adjust switch extract initialize validate clarify mark accept reject wrap keep drop test limit raise pass reset select detect prefer".split())
CONVENTIONAL = re.compile(r"^(?:feat|fix|docs|style|refactor|perf|test|build|ci|chore)(?:\([^\n)]+\))?!?:\s*", re.I)
GENERATED = re.compile(r"(?i)(^|/)(vendor|node_modules|dist|build|\.git)/|(^|/)(package-lock\.json|yarn\.lock|Cargo\.lock)$|\.(min\.js|svg|ipynb)$")
GENERIC = re.compile(r"(?:fix(?:ed|es)? (?:a |the |some )?(?:bugs?|issues?|typos?|tests?)|(?:add|update|make) (?:some |more |the )?(?:changes?|updates?|fixes))\.?", re.I)


def inspect_candidate(row):
    repo, sha = row.get("repo"), row.get("hash")
    if not isinstance(repo, str) or not isinstance(sha, str):
        raise Reject("invalid_identity")
    identity(repo, sha)
    if row.get("license") != "MIT License":
        raise Reject("dataset_license_not_MIT")
    message = subject(row.get("original_message"))
    text = CONVENTIONAL.sub("", message)
    match = re.match(r"[a-zA-Z]+", text)
    if not match or match[0].lower() not in ACTIONS:
        raise Reject("english_action_heuristic")
    if GENERIC.fullmatch(text) or re.search(r"@[\w-]+", message):
        raise Reject("generic_subject_or_mention")
    mods = row.get("mods")
    if not isinstance(mods, list) or not 1 <= len(mods) <= 5:
        raise Reject("processed_file_count")
    for modification in mods:
        if not isinstance(modification, dict):
            raise Reject("processed_missing_diff")
        paths = [modification.get(k) for k in ("old_path", "new_path") if modification.get(k) is not None]
        if not paths or any(not isinstance(p, str) or not safe_path(p) for p in paths):
            raise Reject("processed_path")
        if any(GENERATED.search(p) for p in paths):
            raise Reject("processed_generated_path")
        if len(set(paths)) > 1:
            raise Reject("processed_rename")
        if not isinstance(modification.get("diff"), str):
            raise Reject("processed_missing_diff")
    changes = "\n".join(m["diff"] for m in mods)
    if not changes.strip() or len(changes) > 4000:
        raise Reject("processed_character_budget")
    if SECRET.search(changes) or any((ord(c) < 32 and c not in "\n\r\t") or ord(c) == 127 for c in changes):
        raise Reject("processed_secret_or_control")
    if re.search(r"(?im)^[+ -].*(auto.?generated|do not edit)", changes):
        raise Reject("processed_generated_content")
    representation = json.dumps(mods, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    return {"repo_id": repo.casefold(), "commit_id": sha, "subject": message,
            "language": row.get("language") or "unknown", "processed_mods": representation,
            "processed_hash": hashlib.sha256(representation.encode()).hexdigest(),
            "estimate_text": PREFIX + changes,
            "priority": hashlib.sha256(("42:" + repo.casefold() + ":" + sha).encode()).hexdigest()}


def flush_batch(connection, pending, tokenizer, special_ids, rejected):
    if not pending:
        return 0
    texts = [r["estimate_text"] for r in pending] + [r["subject"] for r in pending]
    ids = tokenizer(texts, add_special_tokens=True, truncation=False, padding=False,
                    return_attention_mask=False, return_token_type_ids=False, verbose=False)["input_ids"]
    kept = 0
    for index, row in enumerate(pending):
        input_ids, target_ids = ids[index], ids[index + len(pending)]
        if len(input_ids) > 512 or len(target_ids) > 64:
            rejected["processed_token_budget"] += 1
            continue
        if special_ids.intersection(input_ids[1:-1]) or special_ids.intersection(target_ids[1:-1]):
            rejected["literal_reserved_or_unknown_token"] += 1
            continue
        try:
            connection.execute("INSERT INTO candidates VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (
                row["commit_id"], row["repo_id"], row["split"], row["shard"], row["row_index"],
                row["subject"], row["language"], row["processed_mods"], row["processed_hash"],
                len(input_ids), len(target_ids), row["priority"],
            ))
            kept += 1
        except sqlite3.IntegrityError:
            rejected["duplicate_commit_or_processed_patch"] += 1
    connection.commit()
    pending.clear()
    return kept


def write_progress(path, report):
    temporary = path.with_suffix(".tmp")
    json_write(temporary, report)
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=Path(r"D:\PushTrackML"))
    args = parser.parse_args()
    if platform.system() != "Windows":
        parser.error("Run data processing natively on Windows")
    temporary = args.workspace / ".tmp"
    temporary.mkdir(exist_ok=True)
    for name in ("TEMP", "TMP", "SQLITE_TMPDIR"):
        os.environ[name] = str(temporary)
    os.environ["HF_HOME"] = str(args.workspace / ".cache" / "huggingface")
    root = args.workspace / "data" / "corpus-0001"
    shards = selected_shards(json.loads((root / "hub-tree.json").read_text()))
    downloads = [json.loads(p.read_text()) for p in (root / "downloads").glob("*.json")]
    if not any(r["status"] == "complete" and r["rows"] == EXPECTED_ROWS for r in downloads):
        parser.error("Require a completed hash-verified corpus download first")
    output = root / "prepared"
    if output.exists():
        parser.error("Prepared output exists; preserve prior evidence")
    output.mkdir()
    for name in ("prepare_corpus.py", "download_corpus.py", "continue_pilot.py", "compare_tokenizers.py", "prepare_pilot.py", "requirements-data.lock"):
        destination = output / "provenance" / name
        destination.parent.mkdir(exist_ok=True)
        shutil.copyfile(Path(__file__).parent / name, destination)
    import pyarrow.parquet as pq

    adapter = OfficialTokenizer(args.workspace / "runs" / "tokenizer-0002" / "codet5-small")
    tokenizer = adapter.tokenizer
    specials = set(tokenizer.all_special_ids)
    connection = sqlite3.connect(output / "candidates.sqlite3")
    connection.execute("CREATE TABLE candidates (commit_id TEXT PRIMARY KEY, repo_id TEXT NOT NULL, split TEXT NOT NULL, shard TEXT NOT NULL, row_index INTEGER NOT NULL, subject TEXT NOT NULL, language TEXT NOT NULL, processed_mods TEXT NOT NULL, processed_hash TEXT NOT NULL UNIQUE, processed_tokens INTEGER NOT NULL, target_tokens INTEGER NOT NULL, priority TEXT NOT NULL)")
    report = {"dataset": DATASET, "revision": REVISION, "status": "running",
              "started_at_utc": dt.datetime.now(dt.UTC).isoformat(), "splits": {},
              "training_ready": 0, "original_source_verified": False,
              "test_read": False, "tokenizer": "official CodeT5-small",
              "temporary_directory": str(temporary),
              "representation": "Published processed modifications; not original complete diffs",
              "english_check": "Conservative action-word heuristic, not independent human annotation"}
    held_out = set()
    for shard in shards:
        if shard["split"] == "validation":
            for batch in pq.ParquetFile(root / "shards" / shard["name"]).iter_batches(batch_size=4096, columns=["repo"]):
                held_out.update(r.casefold() for r in batch.column(0).to_pylist() if isinstance(r, str))
    report["reserved_validation_repositories"] = len(held_out)
    try:
        # Validation first: exact processed-duplicate candidates cannot leak into training.
        for split in ("validation", "train"):
            rejected, scanned, kept, pending = Counter(), 0, 0, []
            for shard in (s for s in shards if s["split"] == split):
                path = root / "shards" / shard["name"]
                with path.open("rb") as file:
                    if hashlib.file_digest(file, "sha256").hexdigest() != shard["sha256"]:
                        raise ValueError(f"Shard integrity failed: {shard['name']}")
                row_index = 0
                for batch in pq.ParquetFile(path).iter_batches(batch_size=128, columns=["repo", "hash", "license", "original_message", "mods", "language"]):
                    for row in batch.to_pylist():
                        scanned += 1
                        try:
                            candidate = inspect_candidate(row)
                            if split == "train" and candidate["repo_id"] in held_out:
                                raise Reject("reserved_validation_repository")
                            candidate.update(split=split, shard=shard["name"], row_index=row_index)
                            pending.append(candidate)
                        except Reject as error:
                            rejected[str(error)] += 1
                        row_index += 1
                        if len(pending) >= 256:
                            kept += flush_batch(connection, pending, tokenizer, specials, rejected)
                kept += flush_batch(connection, pending, tokenizer, specials, rejected)
                report["splits"][split] = {"scanned": scanned, "candidates": kept, "rejections": dict(rejected)}
                write_progress(output / "report.json", report)
                print(f'{split}: {scanned:,} scanned, {kept:,} candidates; {shard["name"]}', flush=True)
            if scanned != EXPECTED_ROWS[split] or kept + sum(rejected.values()) != scanned:
                raise RuntimeError("Candidate accounting does not match the pinned corpus")
        connection.execute("CREATE INDEX candidate_group_order ON candidates(split,repo_id,priority)")
        connection.commit()
        report["languages"] = {}
        report["exports"] = {}
        for split in ("train", "validation"):
            report["splits"][split]["repositories"] = connection.execute("SELECT COUNT(DISTINCT repo_id) FROM candidates WHERE split=?", (split,)).fetchone()[0]
            report["languages"][split] = dict(connection.execute("SELECT language,COUNT(*) FROM candidates WHERE split=? GROUP BY language ORDER BY COUNT(*) DESC", (split,)))
            export = output / (split + "-candidates.jsonl")
            with export.open("x", encoding="utf-8", newline="\n") as file:
                for row in connection.execute("SELECT repo_id,commit_id,shard,row_index,subject,language,processed_mods,processed_hash,processed_tokens,target_tokens FROM candidates WHERE split=? ORDER BY repo_id,priority", (split,)):
                    record = dict(zip(("repo_id", "commit_id", "shard", "row_index", "subject", "language", "processed_mods", "processed_hash", "processed_token_estimate", "target_tokens"), row))
                    record["processed_mods"] = json.loads(record["processed_mods"])
                    record.update(split=split, review_status="unverified_candidate", training_approved=False)
                    file.write(json.dumps(record, ensure_ascii=True) + "\n")
            with export.open("rb") as file:
                report["exports"][export.name] = {"sha256": hashlib.file_digest(file, "sha256").hexdigest(), "bytes": export.stat().st_size}
        report["status"] = "complete_candidate_preparation"
    except Exception as error:
        report["status"] = "stopped"
        report["error"] = f"{type(error).__name__}: {error}"
        raise
    finally:
        report["finished_at_utc"] = dt.datetime.now(dt.UTC).isoformat()
        connection.close()
        write_progress(output / "report.json", report)
    print(json.dumps({k: v for k, v in report.items() if k != "languages"}, indent=2), flush=True)


if __name__ == "__main__":
    main()
