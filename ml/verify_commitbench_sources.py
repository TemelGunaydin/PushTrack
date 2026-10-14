"""Bounded CommitBench source pilot using existing Git reconstruction and audit gates."""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
import datetime as dt
import json
from pathlib import Path
import shutil
import threading
import time

from audit_corpus import INPUTS, audit_repo, changed_text, near_overlap
from continue_pilot import OfficialTokenizer
from prepare_commitbench import DATASET, REVISION, CSV_SHA, environment, file_sha, legacy_inputs
from prepare_corpus import write_progress
from prepare_pilot import digest, json_write
from verify_corpus_sources import ZERO, verify_repository


def source_record(row, candidate):
    """Correct dataset provenance at the adapter boundary, not the shared collector."""
    if row["commit_id"] != candidate["commit_id"] or row["repo_id"] != candidate["repo_id"] or row["message"] != candidate["subject"]:
        raise ValueError("Reconstructed candidate identity/subject mismatch")
    result = dict(row)
    result["dataset"] = {"name": DATASET, "revision": REVISION, "shard": "train.csv",
        "shard_sha256": CSV_SHA, "row_index": candidate["row_index"], "license": "CC-BY-NC-4.0",
        "published_split": "commit-random train; not the repository-split archive",
        "published_diff_sha256": candidate["published_diff_sha256"],
        "published_message_sha256": candidate["published_message_sha256"],
        "published_diff_languages": candidate["published_diff_languages"]}
    result["input_origin"] = "Original complete Git parent-to-commit patch, not the normalized published CSV patch"
    result["usage_status"] = "noncommercial_research_only_pending_quality_and_distribution_clearance"
    result["training_approved"] = False
    return result


def file_pairs(row):
    blobs = {(entry["revision"], entry["path"]): entry["blob_sha"] for entry in row["source_file_screening"]}
    return {(blobs.get((row["parent_id"], path), ZERO), blobs.get((row["commit_id"], path), ZERO)) for path in row["files"]}


def overlap_reason(row, commits, patches, changes, pairs, validation_objects):
    if row["commit_id"] in commits:
        return "legacy_or_duplicate_commit"
    if {row["commit_id"], row["parent_id"]} & validation_objects:
        return "validation_commit_or_parent_overlap"
    if row["patch_id"] in patches:
        return "legacy_or_duplicate_stable_patch"
    change = changed_text(row["diff"])
    if change.strip() and digest(change.encode()) in changes:
        return "legacy_or_duplicate_changed_text"
    if file_pairs(row) & pairs:
        return "legacy_or_duplicate_file_change"
    return None


def run(workspace):
    environment(workspace)
    root = workspace / "data" / "commitbench-0001"
    prepared = root / "prepared"
    preparation = json.loads((prepared / "report.json").read_text())
    if preparation["status"] != "complete_candidate_preparation" or file_sha(root / "train.csv") != CSV_SHA:
        raise ValueError("Verified CommitBench preparation required")
    if file_sha(prepared / "source-pilot.json") != preparation["pilot_sha256"]:
        raise ValueError("Changed pilot selection")
    candidates = json.loads((prepared / "source-pilot.json").read_text())["candidates"]
    if not 0 < len(candidates) <= 200 or len({row["commit_id"] for row in candidates}) != len(candidates):
        raise ValueError("Expected distinct bounded pilot candidates")
    grouped = defaultdict(list)
    for row in candidates:
        grouped[row["repo_id"]].append(row)
    if len(grouped) > 20 or any(len(rows) > 10 for rows in grouped.values()):
        raise ValueError("Pilot repository budgets exceeded")
    for split, (_, expected) in INPUTS.items():
        path = workspace / "data" / "corpus-0001" / "sources-0001" / f"{split}-pending.jsonl"
        if file_sha(path) != expected:
            raise ValueError("Legacy source/hold evidence changed")
    train, held, legacy_commits, old_rows = legacy_inputs(workspace)
    if any(row["split"] != "train" or row["repo_id"] not in train or row["repo_id"] in held or row["commit_id"] in legacy_commits for row in candidates):
        raise ValueError("Selection crossed split or legacy-hold boundaries")
    output = root / "sources-0001"
    if output.exists():
        raise ValueError("Preserve previous source-pilot output")
    for name in ("licenses", "source-files", "repos", "provenance"):
        (output / name).mkdir(parents=True, exist_ok=False)
    for name in ("verify_commitbench_sources.py", "test_verify_commitbench_sources.py", "prepare_commitbench.py", "verify_corpus_sources.py", "audit_corpus.py", "prepare_corpus.py", "continue_pilot.py", "compare_tokenizers.py", "prepare_pilot.py", "requirements-data.lock"):
        shutil.copyfile(Path(__file__).parent / name, output / "provenance" / name)
    # Initialize in the main thread before shared Transformers imports in workers.
    OfficialTokenizer(workspace / "runs" / "tokenizer-0002" / "codet5-small")
    report = {"status": "running", "started_at_utc": dt.datetime.now(dt.UTC).isoformat(),
        "dataset": DATASET, "revision": REVISION, "license": "CC-BY-NC-4.0", "csv_sha256": CSV_SHA,
        "selected_candidates": len(candidates), "selected_repositories": len(grouped),
        "budgets": {"seconds": 2700, "git_storage_threshold_bytes": 1_000_000_000, "parallel_repositories": 2},
        "training_approved": False, "test_read": False, "optimizer_updates": 0,
        "canonical_family_status": "Existing metadata reused; unresolved identities remain, no exhaustive clearance",
        "pilot_sha256": preparation["pilot_sha256"], "source_sha256": file_sha(Path(__file__))}
    deadline = time.monotonic() + 2700
    stop = threading.Event()
    jobs = [(repo, "train", rows) for repo, rows in grouped.items()]
    indexed = {row["commit_id"]: row for row in candidates}
    counts, outcomes, reconstructed = Counter(), [], []
    stored = attempted = 0
    try:
        with (output / "repositories.jsonl").open("x", encoding="utf-8") as log:
            for offset in range(0, len(jobs), 2):
                if stop.is_set() or time.monotonic() >= deadline or stored >= 1_000_000_000:
                    break
                chunk = jobs[offset:offset + 2]
                with ThreadPoolExecutor(max_workers=2) as pool:
                    results = list(pool.map(lambda job: verify_repository(job, workspace, output, stop, deadline), chunk))
                for job, result in zip(chunk, results):
                    rows = result.pop("rows")
                    attempted += len(job[2])
                    stored += result["stored_git_bytes"]
                    if result["status"] != "complete":
                        counts["repository_failed_or_stopped"] += len(job[2])
                    else:
                        if len(rows) + sum(result["rejections"].values()) != len(job[2]):
                            raise ValueError("Source reconstruction accounting mismatch")
                        counts.update(result["rejections"])
                        reconstructed.extend(source_record(row, indexed[row["commit_id"]]) for row in rows)
                    log.write(json.dumps(result) + "\n"); log.flush()
                    report.update(attempted_candidates=attempted, reconstructed=len(reconstructed), git_storage_bytes=stored, source_rejections=dict(counts))
                    write_progress(output / "report.json", report)
                    print(f"{attempted}/{len(candidates)} candidates attempted; {len(reconstructed)} reconstructed; {job[0]}: {result['status']}", flush=True)
        counts["unattempted_at_budget_stop"] += len(candidates) - attempted
        json_write(output / "reconstructed.json", reconstructed)
        # Independently audit only this new bounded pilot, not the old 11,000 rows.
        by_repo = defaultdict(list)
        for row in reconstructed:
            by_repo[row["repo_id"]].append(row)
        integrity, valid = [], []
        for repo, rows in by_repo.items():
            result = audit_repo((repo, rows), output, workspace)
            integrity.append(result)
            passed = {row["commit_id"] for row in result["rows"]}
            errors = {row.get("commit_id") for row in result["errors"]}
            for row in rows:
                if result["errors"] or row["commit_id"] not in passed or row["commit_id"] in errors:
                    counts["integrity_audit_hold"] += 1
                else:
                    row["integrity_status"] = "complete_original_diff_applies_to_exact_snapshots"
                    row["inspection_flags"] = next(value["flags"] for value in result["rows"] if value["commit_id"] == row["commit_id"])
                    valid.append(row)
        json_write(output / "integrity.json", integrity)
        patches = {row["patch_id"] for row in old_rows}
        changes = {digest(text.encode()) for row in old_rows if (text := changed_text(row["diff"])).strip()}
        pairs = set().union(*(file_pairs(row) for row in old_rows))
        validation_rows = [row for row in old_rows if row["split"] == "validation"]
        validation_objects = {sha for row in validation_rows for sha in (row["commit_id"], row["parent_id"])}
        near = near_overlap(validation_rows + valid)
        near_ids = {row["train_commit"] for row in near}
        json_write(output / "near-validation-overlap.json", near)
        accepted = []
        for row in valid:
            reason = overlap_reason(row, legacy_commits, patches, changes, pairs, validation_objects)
            if not reason and row["commit_id"] in near_ids:
                reason = "near_validation_changed_tokens"
            if reason:
                counts[reason] += 1
                outcomes.append({"commit_id": row["commit_id"], "reason": reason})
                continue
            accepted.append(row)
            legacy_commits.add(row["commit_id"]); patches.add(row["patch_id"])
            changes.add(digest(changed_text(row["diff"]).encode())); pairs.update(file_pairs(row))
        if len(accepted) + sum(counts.values()) != len(candidates):
            raise ValueError("Final source-pilot accounting mismatch")
        export = output / "train-pending.jsonl"
        with export.open("x", encoding="utf-8", newline="\n") as file:
            for row in accepted:
                file.write(json.dumps(row, ensure_ascii=True) + "\n")
        json_write(output / "overlap-holds.json", outcomes)
        sample = sorted(accepted, key=lambda row: digest(("commitbench-quality-42:" + row["commit_id"]).encode()))[:20]
        json_write(output / "quality-sample.json", {"policy": "First twenty hash ranks of commitbench-quality-42 plus identity over all pending survivors, no model outputs or replacements", "rows": sample})
        legacy_inputs(workspace)
        if file_sha(root / "train.csv") != CSV_SHA:
            raise ValueError("Published data changed")
        report.update(status="complete_bounded_source_pilot", accepted=len(accepted), accepted_repositories=len({r["repo_id"] for r in accepted}),
            source_rejections=dict(counts), unattempted_candidates=len(candidates)-attempted,
            integrity_audited=len(reconstructed), integrity_errors=sum(len(result["errors"]) for result in integrity),
            pending_export_sha256=file_sha(export), quality_sample_sha256=file_sha(output / "quality-sample.json"),
            semantic_reviewed=0, note="Source/overlap checks are not semantic approval, full family clearance, or product licensing approval")
    except Exception as error:
        report.update(status="stopped", error=f"{type(error).__name__}: {error}")
        raise
    finally:
        report["finished_at_utc"] = dt.datetime.now(dt.UTC).isoformat()
        write_progress(output / "report.json", report)
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=Path(r"D:\PushTrackML"))
    run(parser.parse_args().workspace)
