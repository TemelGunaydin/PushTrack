"""Prepare the pinned CommitBench TRAIN CSV, never train or inspect its test split."""
import argparse
from collections import Counter
import csv
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
from prepare_corpus import ACTIONS, CONVENTIONAL, GENERATED, GENERIC, write_progress
from prepare_pilot import PREFIX, SECRET, Reject, digest, identity, json_write, safe_path, subject

DATASET = "Maxscha/commitbench"
REVISION = "1500792cd6998308da046ba72b688156b2ffa471"
CSV_BYTES = 1_051_789_145
CSV_SHA = "23adc5ca32088e9991882ccd252b0579b95d22d07dc9b0bce739f4e920c96f04"
FROZEN = {"train.jsonl": "5dd4d286b73bea89456bdb2cb3c5cb23a3757ad38a6baaa37099fe5f0a4d4269",
          "validation.jsonl": "76b9d83b60741738c29dc53f8629ec4c0e08434427595a5191682f19f42ba2ee"}


def file_sha(path):
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def environment(workspace):
    if platform.system() != "Windows":
        raise RuntimeError("Process real data natively on Windows")
    for name in ("TEMP", "TMP", "SQLITE_TMPDIR"):
        os.environ[name] = str(workspace / ".tmp")
    os.environ.update(HF_HUB_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1",
                      HF_HOME=str(workspace / ".cache" / "huggingface"))
    if shutil.disk_usage(workspace).free < 20_000_000_000:
        raise RuntimeError("Preserve the 20 GB disk reserve")


def legacy_inputs(workspace):
    corpus = workspace / "data" / "corpus-0001"
    for name, expected in FROZEN.items():
        if file_sha(corpus / "audit-0002" / "post-review-pending" / name) != expected:
            raise ValueError("Frozen data changed")
    database = corpus / "prepared" / "candidates.sqlite3"
    with sqlite3.connect(f"{database.as_uri()}?mode=ro", uri=True) as connection:
        train = {r[0] for r in connection.execute("SELECT DISTINCT repo_id FROM candidates WHERE split='train'")}
        validation = {r[0] for r in connection.execute("SELECT DISTINCT repo_id FROM candidates WHERE split='validation'")}
    rows = []
    # Include the held records as well: changing datasets must not resurrect holds.
    for split in ("train", "validation"):
        rows.extend(json.loads(line) for line in (corpus / "sources-0001" / f"{split}-pending.jsonl").read_bytes().splitlines())
    commits = {row["commit_id"] for row in rows}
    for path in (workspace / "data").glob("pilot-*/*.jsonl"):
        for line in path.read_bytes().splitlines():
            row = json.loads(line)
            if isinstance(row.get("commit_id"), str):
                commits.add(row["commit_id"])
    families = json.loads((corpus / "audit-0002" / "families.json").read_text())["repositories"]
    held_families = {value["family_id"] for name, value in families.items() if name in validation}
    for name, value in families.items():
        if value["family_id"] in held_families:
            validation.update((name, value["canonical_name"], value["family_name"]))
    return train - validation, validation, commits, rows


def project_identity(project):
    # Publisher serializes org + '_' + repository. GitHub owners cannot contain '_'.
    if not isinstance(project, str):
        raise Reject("invalid_project")
    owner, separator, repo = project.partition("_")
    if not separator or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]{0,38}", owner) or not repo:
        raise Reject("invalid_project")
    identity(owner + "/" + repo, "a" * 40)
    return (owner + "/" + repo).casefold()


def inspect_record(row, index, train_repos, held_repos, legacy_commits):
    if row.get("split") != "train":
        raise ValueError("Non-training row in the pinned training file; stop")
    repo = project_identity(row.get("project"))
    sha = row.get("hash")
    if not isinstance(sha, str):
        raise Reject("invalid_identity")
    identity(repo, sha)
    if repo in held_repos or repo not in train_repos:
        raise Reject("outside_reserved_training_repository_universe")
    if sha in legacy_commits:
        raise Reject("legacy_identity_including_holds")
    message = subject(row.get("message"))
    text = CONVENTIONAL.sub("", message)
    action = re.match(r"[A-Za-z]+", text)
    if not action or action[0].casefold() not in ACTIONS:
        raise Reject("english_action_heuristic")
    if GENERIC.fullmatch(text) or re.search(r"@[\w-]+", message):
        raise Reject("generic_subject_or_mention")
    diff = row.get("diff")
    if not isinstance(diff, str) or not diff.strip() or len(diff) > 12000:
        raise Reject("published_diff_character_budget")
    if SECRET.search(diff) or any((ord(c) < 32 and c not in "\n\r\t") or ord(c) == 127 for c in diff):
        raise Reject("published_secret_or_control")
    headers = [line for line in diff.splitlines() if line.startswith("diff --git ")]
    if not 1 <= len(headers) <= 5:
        raise Reject("published_file_count")
    for header in headers:
        match = re.fullmatch(r"diff --git a/(\S+) b/(\S+)", header)
        if not match or match[1] != match[2] or not safe_path(match[1]) or len(match[1]) > 200:
            raise Reject("published_path_or_rename")
        if GENERATED.search(match[1]):
            raise Reject("published_generated_path")
    return {"repo_id": repo, "commit_id": sha, "split": "train", "shard": "train.csv", "row_index": index,
            "subject": message, "published_diff": diff, "published_diff_sha256": digest(diff.encode()),
            "published_message_sha256": digest(row["message"].encode()),
            "published_diff_languages": row.get("diff_languages"),
            "priority": digest(("commitbench-pilot-42:" + repo + ":" + sha).encode())}


def flush(connection, pending, adapter, rejected):
    if not pending:
        return 0
    texts = [PREFIX + row["published_diff"] for row in pending] + [row["subject"] for row in pending]
    sequences = adapter.tokenizer(texts, add_special_tokens=True, truncation=False, padding=False,
        return_attention_mask=False, return_token_type_ids=False, verbose=False)["input_ids"]
    specials = set(adapter.tokenizer.all_special_ids)
    kept = 0
    for index, row in enumerate(pending):
        inputs, labels = sequences[index], sequences[index + len(pending)]
        if len(inputs) > 512 or len(labels) > 64:
            rejected["published_token_budget"] += 1
            continue
        if specials.intersection(inputs[1:-1]) or specials.intersection(labels[1:-1]):
            rejected["reserved_or_unknown_token"] += 1
            continue
        # The official adapter independently enforces round-trip and marker rules.
        try:
            if adapter.encode(texts[index]).ids != inputs or adapter.encode(row["subject"]).ids != labels:
                raise ValueError("Batch tokenizer differs from official adapter")
        except Reject as error:
            rejected[str(error)] += 1
            continue
        row.update(published_input_tokens=len(inputs), target_tokens=len(labels),
                   training_approved=False, review_status="unverified_commitbench_candidate")
        try:
            connection.execute("INSERT INTO candidates VALUES (?,?,?,?,?)", (
                row["commit_id"], row["repo_id"], row["published_diff_sha256"], row["priority"], json.dumps(row, ensure_ascii=True)))
            kept += 1
        except sqlite3.IntegrityError:
            rejected["duplicate_commit_or_published_diff"] += 1
    connection.commit()
    pending.clear()
    return kept


def choose_pilot(connection, legacy_repos):
    repositories = [r[0] for r in connection.execute("SELECT repo_id FROM candidates GROUP BY repo_id")]
    # New repositories relative to earlier SOURCE-checked records, not unseen test repos.
    repositories.sort(key=lambda repo: (repo in legacy_repos, digest(("commitbench-repositories-42:" + repo).encode())))
    selected = []
    for repo in repositories[:20]:
        selected.extend(json.loads(r[0]) for r in connection.execute(
            "SELECT record FROM candidates WHERE repo_id=? ORDER BY priority LIMIT 10", (repo,)))
    return selected


def run(workspace):
    environment(workspace)
    root = workspace / "data" / "commitbench-0001"
    output = root / "prepared"
    if output.exists():
        raise ValueError("Preparation exists; preserve evidence")
    source = root / "train.csv"
    if source.stat().st_size != CSV_BYTES or file_sha(source) != CSV_SHA:
        raise ValueError("Pinned training CSV integrity mismatch")
    if json.loads((root / "download" / "report.json").read_text())["status"] != "verified":
        raise ValueError("Verified train-only download required")
    train, held, legacy, old_rows = legacy_inputs(workspace)
    adapter = OfficialTokenizer(workspace / "runs" / "tokenizer-0002" / "codet5-small")
    output.mkdir()
    provenance = output / "provenance"
    provenance.mkdir()
    for name in ("prepare_commitbench.py", "test_prepare_commitbench.py", "prepare_corpus.py", "continue_pilot.py", "compare_tokenizers.py", "prepare_pilot.py", "requirements-data.lock"):
        shutil.copyfile(Path(__file__).parent / name, provenance / name)
    connection = sqlite3.connect(output / "candidates.sqlite3")
    connection.execute("CREATE TABLE candidates (commit_id TEXT PRIMARY KEY,repo_id TEXT NOT NULL,diff_sha TEXT UNIQUE NOT NULL,priority TEXT NOT NULL,record TEXT NOT NULL)")
    report = {"status": "running", "started_at_utc": dt.datetime.now(dt.UTC).isoformat(),
              "dataset": DATASET, "revision": REVISION, "license": "CC-BY-NC-4.0", "csv_sha256": CSV_SHA,
              "source_sha256": file_sha(Path(__file__)), "training_approved": False,
              "test_read": False, "validation_acquired": False, "published_split": "commit-random train, not repo-split",
              "eligible_repository_names": len(train), "reserved_repository_names": len(held),
              "excluded_legacy_identities": len(legacy), "semantic_review": "pending",
              "limitations": "Not an exhaustive fork/pretraining-overlap or privacy/license clearance. Published diffs may be normalized; source reconstruction remains mandatory."}
    counts, pending, scanned, kept = Counter(), [], 0, 0
    csv.field_size_limit(2_000_000)
    try:
        with source.open(encoding="utf-8", newline="") as file:
            reader = csv.DictReader(file)
            if reader.fieldnames != ["hash", "diff", "message", "project", "split", "diff_languages"]:
                raise ValueError(f"Unexpected CSV header: {reader.fieldnames}")
            for index, row in enumerate(reader):
                if None in row or any(value is None for value in row.values()):
                    raise ValueError("Malformed CSV row")
                scanned += 1
                try:
                    pending.append(inspect_record(row, index, train, held, legacy))
                except Reject as error:
                    counts[str(error)] += 1
                if len(pending) >= 256:
                    kept += flush(connection, pending, adapter, counts)
                if scanned % 100000 == 0:
                    report.update(scanned=scanned, candidates=kept, pending=len(pending), rejections=dict(counts))
                    write_progress(output / "report.json", report)
                    print(f"{scanned:,} published training rows inspected; {kept:,} candidates", flush=True)
        kept += flush(connection, pending, adapter, counts)
        if scanned != kept + sum(counts.values()):
            raise RuntimeError("Preparation accounting failed")
        connection.execute("CREATE INDEX candidate_order ON candidates(repo_id,priority)")
        connection.commit()
        selected = choose_pilot(connection, {row["repo_id"] for row in old_rows})
        json_write(output / "source-pilot.json", {"policy": "20 repositories, <=10 candidates each, new-to-source-check repositories first, deterministic hash order; not a training subset",
            "dataset": DATASET, "revision": REVISION, "csv_sha256": CSV_SHA, "candidates": selected})
        report.update(status="complete_candidate_preparation", scanned=scanned, candidates=kept, pending=0,
            repositories=connection.execute("SELECT COUNT(DISTINCT repo_id) FROM candidates").fetchone()[0],
            rejections=dict(counts), source_pilot_count=len(selected), source_pilot_repositories=len({r["repo_id"] for r in selected}),
            pilot_sha256=file_sha(output / "source-pilot.json"), candidate_db_sha256=None)
        if file_sha(source) != CSV_SHA:
            raise ValueError("Published training source changed during preparation")
        legacy_inputs(workspace)  # Recheck frozen inputs, without writing any old files.
    except Exception as error:
        report.update(status="stopped", error=f"{type(error).__name__}: {error}")
        raise
    finally:
        connection.close()
        report["candidate_db_sha256"] = file_sha(output / "candidates.sqlite3")
        report["finished_at_utc"] = dt.datetime.now(dt.UTC).isoformat()
        write_progress(output / "report.json", report)
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=Path(r"D:\PushTrackML"))
    run(parser.parse_args().workspace)
