"""Fixed, bounded CommitBench source expansion; no training or label rewriting."""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
import datetime as dt
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import threading
import time

from audit_corpus import INPUTS, audit_repo, changed_text, near_overlap
from continue_pilot import OfficialTokenizer
from prepare_commitbench import CSV_SHA, DATASET, REVISION, environment, file_sha, legacy_inputs
from prepare_corpus import write_progress
from prepare_pilot import Reject, StopCollection, digest, json_write
from verify_commitbench_sources import file_pairs, overlap_reason, source_record
from verify_corpus_sources import GitSource, ZERO, build_plan, materialize

TARGET = 10000
ATTEMPT_PER_REPO = 192
RETAIN_PER_REPO = 100
SECONDS = 7200
GIT_BYTES = 8_000_000_000
REPO_BYTES = 256_000_000
SAMPLE = 40


def tree_hashes(directory):
    return {str(path.relative_to(directory)): file_sha(path) for path in sorted(directory.rglob("*")) if path.is_file()}


class ExpansionGit(GitSource):
    """Copy immutable cached objects into a NEW owned repository; fetch missing blobs only."""
    def __init__(self, directory, repo, temporary, stop, deadline, seed=None):
        super().__init__(directory, repo, temporary, stop, deadline)
        self.env["GIT_NO_LAZY_FETCH"] = "1"
        self.reused_blob_count = 0
        if seed is not None:
            if not (seed / "HEAD").is_file() or (seed / "objects" / "info" / "alternates").exists():
                raise ValueError("Expected a self-contained earlier bare cache")
            if sum(path.stat().st_size for path in seed.rglob("*") if path.is_file()) > REPO_BYTES:
                raise Reject("seed_repository_disk_budget")
            shutil.copytree(seed / "objects", directory / "objects", dirs_exist_ok=True)
            if (seed / "shallow").exists():
                shutil.copyfile(seed / "shallow", directory / "shallow")
            # Only new-repository configuration is modified. No prior refs/config copied.
            self.run("config", "remote.origin.promisor", "true")
            self.run("config", "remote.origin.partialclonefilter", "blob:none")

    def fetch(self, shas, commits=False):
        if not shas:
            return
        # The base validates SHA syntax; validate before even a local batch request.
        import re
        if any(not isinstance(sha, str) or not re.fullmatch(r"[a-f0-9]{40}", sha) for sha in shas):
            raise Reject("invalid_git_fetch_identity")
        if not commits:
            raw = self.run("cat-file", "--batch-check", data=("\n".join(shas) + "\n").encode(), limit=len(shas) * 100)
            lines = raw.decode("ascii").splitlines()
            if len(lines) != len(shas):
                raise ValueError("Local object coverage changed")
            missing = []
            for sha, line in zip(shas, lines):
                parts = line.split()
                if parts == [sha, "missing"]:
                    missing.append(sha)
                elif len(parts) == 3 and parts[0] == sha and parts[1] == "blob" and parts[2].isdigit():
                    self.reused_blob_count += 1
                else:
                    raise ValueError("Unexpected cached object identity/type")
            shas = missing
        super().fetch(shas, commits=commits)


def select_jobs(connection, excluded, train, held):
    repositories = [row[0] for row in connection.execute("SELECT DISTINCT repo_id FROM candidates")]
    repositories.sort(key=lambda repo: digest(("commitbench-expansion-repositories-42:" + repo).encode()))
    jobs = []
    for repo in repositories:
        if repo not in train or repo in held:
            continue
        rows = []
        for commit, text in connection.execute("SELECT commit_id,record FROM candidates WHERE repo_id=? ORDER BY priority", (repo,)):
            if commit in excluded:
                continue
            row = json.loads(text)
            if row["repo_id"] != repo or row["commit_id"] != commit or row["split"] != "train" or row["training_approved"] is not False:
                raise ValueError("Unexpected candidate identity/split")
            rows.append(row)
            if len(rows) == ATTEMPT_PER_REPO:
                break
        if rows:
            jobs.append((repo, rows))
    return jobs


def collect_repository(job, workspace, output, stop, deadline):
    repo, candidates = job
    result = {"repo_id": repo, "selected": len(candidates), "status": "complete", "rows": [], "outcomes": [],
              "reconstructed": 0, "integrity_errors": [], "integrity_flags": {}, "reused_blob_count": 0}
    path = output / "repos" / digest(repo.encode())[:24]
    seeds = [workspace / "data" / "commitbench-0001" / "sources-0001" / "repos" / path.name,
             workspace / "data" / "corpus-0001" / "sources-0001" / "repos" / path.name]
    seed = next((source for source in seeds if (source / "HEAD").is_file()), None)
    seed_before = tree_hashes(seed) if seed else None
    if seed:
        result["seed_cache"] = str(seed)
        result["seed_tree_sha256"] = digest(json.dumps(seed_before, sort_keys=True).encode())
    try:
        git = ExpansionGit(path, repo, workspace / ".tmp", stop, deadline, seed)
        git.fetch([row["commit_id"] for row in candidates], commits=True)
        plans, blobs = [], set()
        for candidate in candidates:
            try:
                plan = build_plan(git, candidate)
                plans.append(plan)
                blobs.update(blob for file in plan["files"] for blob in (file["old_blob"], file["new_blob"]) if blob != ZERO)
                blobs.update(blob for paths in plan["notices"].values() for blob in paths.values())
            except (Reject, UnicodeError) as error:
                result["outcomes"].append({"commit_id": candidate["commit_id"], "reason": str(error) if isinstance(error, Reject) else "source_encoding"})
        git.fetch(sorted(blobs))
        adapter = OfficialTokenizer(workspace / "runs" / "tokenizer-0002" / "codet5-small")
        reconstructed = []
        for plan in plans:
            if len(reconstructed) >= RETAIN_PER_REPO:
                result["outcomes"].append({"commit_id": plan["candidate"]["commit_id"], "reason": "unmaterialized_per_repository_cap"})
                continue
            try:
                reconstructed.append(source_record(materialize(git, plan, adapter, output), plan["candidate"]))
            except (Reject, UnicodeError) as error:
                result["outcomes"].append({"commit_id": plan["candidate"]["commit_id"], "reason": str(error) if isinstance(error, Reject) else "source_encoding"})
        result["reconstructed"] = len(reconstructed)
        result["reused_blob_count"] = git.reused_blob_count
        result["rows"] = reconstructed
        if len(result["rows"]) + len(result["outcomes"]) != len(candidates):
            raise ValueError("Repository source/audit accounting mismatch")
    except StopCollection as error:
        stop.set()
        result.update(status="stopped", error=str(error))
    except Exception as error:
        result.update(status="repository_failed", error=f"{type(error).__name__}: {error}")
    finally:
        result["stored_git_bytes"] = sum(file.stat().st_size for file in path.rglob("*") if file.is_file()) if path.exists() else 0
        if seed and tree_hashes(seed) != seed_before:
            stop.set()
            raise ValueError("Original seed cache changed")
    return result


def audit_result(result, output, workspace):
    # All batch writers have finished before snapshot/notice readers start.
    rows = result["rows"]
    if not rows:
        return
    audit = audit_repo((result["repo_id"], rows), output, workspace)
    result["integrity_errors"] = audit["errors"]
    result["fsck"] = audit["fsck"]
    result["integrity_flags"] = {row["commit_id"]: row["flags"] for row in audit["rows"]}
    result["rows"] = []
    for row in rows:
        if audit["errors"] or row["commit_id"] not in result["integrity_flags"]:
            result["outcomes"].append({"commit_id": row["commit_id"], "reason": "integrity_audit_hold"})
        else:
            row.update(integrity_status="complete_original_diff_applies_to_exact_snapshots",
                       inspection_flags=result["integrity_flags"][row["commit_id"]])
            result["rows"].append(row)


def protected_inputs(workspace):
    base = workspace / "data" / "commitbench-0001"
    primary = workspace / "runs" / "training-0004" / "quality-comparison-0001" / "sample.json"
    if file_sha(primary) != "825382a8f409e1f493428a22627b7ce48ad7cd119724d7c1e2bd1a61b139f129":
        raise ValueError("Earlier training evidence changed")
    protected = dict(json.loads(primary.read_text())["input_artifacts"])
    for name in ("sample.json", "review.json", "verification.json", "final-epoch-secondary.json"):
        path = primary.parent / name
        protected[str(path)] = file_sha(path)
    for split, (_, expected) in INPUTS.items():
        path = workspace / "data" / "corpus-0001" / "sources-0001" / f"{split}-pending.jsonl"
        if file_sha(path) != expected:
            raise ValueError("Legacy source/hold data changed")
        protected[str(path)] = expected
    proof = json.loads((base / "offline-verification.json").read_text())
    if proof["status"] != "passed":
        raise ValueError("Earlier CommitBench verification required")
    for relative, key in (("prepared/candidates.sqlite3", "candidate_db_sha256"),
                          ("sources-0001/train-pending.jsonl", "pending_export_sha256"),
                          ("sources-0001/quality-review.json", "quality_review_sha256")):
        path = base / relative
        if file_sha(path) != proof[key]:
            raise ValueError("Earlier CommitBench proof/input changed")
        protected[str(path)] = proof[key]
    protected[str(base / "train.csv")] = CSV_SHA
    for directory in (base / "prepared", base / "sources-0001", workspace / "runs" / "target-proposal-0001"):
        for path in directory.glob("*.json*"):
            protected[str(path)] = file_sha(path)
    return protected


def check_protected(protected):
    for name, expected in protected.items():
        if file_sha(Path(name)) != expected:
            raise ValueError(f"Changed protected artifact: {Path(name).name}")


def quality_sample(rows):
    return sorted(rows, key=lambda row: digest(("commitbench-expansion-quality-42:" + row["commit_id"]).encode()))[:SAMPLE]


def run(workspace):
    environment(workspace)
    base = workspace / "data" / "commitbench-0001"
    output = base / "sources-0002"
    if output.exists():
        raise ValueError("Preserve completed/stopped expansion; output must be new")
    protected = protected_inputs(workspace)
    check_protected(protected)
    train, held, commits, old_rows = legacy_inputs(workspace)
    pilot = json.loads((base / "prepared" / "source-pilot.json").read_text())["candidates"]
    # Every prior attempted pilot identity stays excluded, including rejected/uncertain ones.
    commits.update(row["commit_id"] for row in pilot)
    old_rows.extend(json.loads(line) for line in (base / "sources-0001" / "train-pending.jsonl").read_bytes().splitlines())
    old_rows.extend(json.loads((base / "sources-0001" / "reconstructed.json").read_text()))
    patches = {row["patch_id"] for row in old_rows}
    changes = {digest(text.encode()) for row in old_rows if (text := changed_text(row["diff"])).strip()}
    pairs = set().union(*(file_pairs(row) for row in old_rows))
    validation = [row for row in old_rows if row["split"] == "validation"]
    validation_objects = {sha for row in validation for sha in (row["commit_id"], row["parent_id"])}
    database = base / "prepared" / "candidates.sqlite3"
    with sqlite3.connect(f"{database.as_uri()}?mode=ro", uri=True) as connection:
        jobs = select_jobs(connection, commits, train, held)
    all_candidates = [row for _, rows in jobs for row in rows]
    OfficialTokenizer(workspace / "runs" / "tokenizer-0002" / "codet5-small")
    for name in ("repos", "licenses", "source-files", "provenance"):
        (output / name).mkdir(parents=True)
    for name in ("expand_commitbench.py", "test_expand_commitbench.py", "verify_commitbench_sources.py", "prepare_commitbench.py", "verify_corpus_sources.py", "audit_corpus.py", "continue_pilot.py", "compare_tokenizers.py", "prepare_corpus.py", "prepare_pilot.py", "requirements-data.lock"):
        shutil.copyfile(Path(__file__).parent / name, output / "provenance" / name)
    json_write(output / "protected-inputs.json", protected)
    json_write(output / "selection.json", {"dataset": DATASET, "revision": REVISION, "csv_sha256": CSV_SHA,
        "repository_order": "SHA-256 of commitbench-expansion-repositories-42: plus repo",
        "candidate_order": "Existing pinned candidate priority; skip all earlier source/pilot identities",
        "quality_sample_policy": "First forty SHA-256 ranks of commitbench-expansion-quality-42: plus identity, no predictions or replacements",
        "repository_count": len(jobs), "candidate_count": len(all_candidates), "candidates": all_candidates})
    report = {"status": "running", "started_at_utc": dt.datetime.now(dt.UTC).isoformat(),
        "dataset": DATASET, "revision": REVISION, "license": "CC-BY-NC-4.0", "target": TARGET,
        "budgets": {"git_seconds": SECONDS, "git_storage_threshold_bytes": GIT_BYTES,
            "per_repository_git_bytes": REPO_BYTES, "attempt_per_repository": ATTEMPT_PER_REPO,
            "retain_per_repository": RETAIN_PER_REPO, "parallel_repositories": 2, "disk_reserve_bytes": 20_000_000_000},
        "selection_sha256": file_sha(output / "selection.json"), "selected_candidates": len(all_candidates),
        "selected_repositories": len(jobs), "accepted": 0, "repositories_checked": 0, "rejections": {},
        "test_read": False, "new_validation_acquired": False, "optimizer_updates": 0,
        "training_approved": False, "quality_sample_size": SAMPLE, "source_sha256": file_sha(Path(__file__)),
        "quality_status": "Training-only assistant sample pending, most subjects not semantically reviewed",
        "family_status": "Known metadata reused; unresolved identities/pretraining/near-copy risks remain",
        "note": "Storage checked after batches, not an exact transfer-byte cap; two-hour deadline for network/reconstruction, read-only audits may finish afterward"}
    accepted, outcomes, counts, near_hits = [], [], Counter(), []
    stored = attempted = reconstructed = reused = 0
    stop, deadline = threading.Event(), time.monotonic() + SECONDS
    try:
        with (output / "repositories.jsonl").open("x", encoding="utf-8") as log, (output / "train-pending.jsonl").open("x", encoding="utf-8", newline="\n") as export:
            for offset in range(0, len(jobs), 2):
                if stop.is_set() or time.monotonic() >= deadline or stored >= GIT_BYTES or len(accepted) >= TARGET:
                    break
                chunk = jobs[offset:offset + 2]
                with ThreadPoolExecutor(max_workers=2) as pool:
                    results = list(pool.map(lambda job: collect_repository(job, workspace, output, stop, deadline), chunk))
                for job, result in zip(chunk, results):
                    if result["status"] == "complete":
                        audit_result(result, output, workspace)
                    rows = result.pop("rows")
                    stored += result["stored_git_bytes"]
                    attempted += len(job[1]); reconstructed += result["reconstructed"]; reused += result["reused_blob_count"]
                    report["repositories_checked"] += 1
                    if result["status"] != "complete":
                        result["outcomes"] = [{"commit_id": row["commit_id"], "reason": "repository_failed_or_stopped"} for row in job[1]]
                        rows = []
                    outcomes.extend(result["outcomes"])
                    counts.update(row["reason"] for row in result["outcomes"])
                    near = near_overlap(validation + rows)
                    near_hits.extend(near)
                    near_ids = {row["train_commit"] for row in near}
                    for row in rows:
                        reason = overlap_reason(row, commits, patches, changes, pairs, validation_objects)
                        if not reason and row["commit_id"] in near_ids:
                            reason = "near_validation_changed_tokens"
                        if not reason and len(accepted) >= TARGET:
                            reason = "unretained_at_global_target"
                        if reason:
                            outcomes.append({"commit_id": row["commit_id"], "reason": reason}); counts[reason] += 1
                        else:
                            accepted.append(row); commits.add(row["commit_id"]); patches.add(row["patch_id"])
                            changes.add(digest(changed_text(row["diff"]).encode())); pairs.update(file_pairs(row))
                            export.write(json.dumps(row, ensure_ascii=True) + "\n")
                    export.flush()
                    log.write(json.dumps(result, ensure_ascii=True) + "\n"); log.flush()
                    report.update(accepted=len(accepted), attempted_candidates=attempted, reconstructed=reconstructed,
                        git_storage_bytes=stored, reused_blob_count=reused, rejections=dict(counts))
                    write_progress(output / "report.json", report)
                    print(f"{len(accepted):,}/{TARGET:,} additional pending; {report['repositories_checked']} repos checked; {job[0]}: {result['status']}", flush=True)
        if len(accepted) + sum(counts.values()) != attempted:
            raise ValueError("Expansion attempted-candidate accounting mismatch")
        sample = quality_sample(accepted)
        json_write(output / "quality-sample.json", {"policy": "First forty identity hash ranks declared in selection.json before collection", "rows": sample})
        json_write(output / "outcomes.json", outcomes)
        json_write(output / "near-validation-overlap.json", near_hits)
        manifest = {"version": "commitbench-source-expansion-0001-pending", "dataset": DATASET, "revision": REVISION,
            "license": "CC-BY-NC-4.0", "train": {"path": str(output / "train-pending.jsonl"), "rows": len(accepted),
                "sha256": file_sha(output / "train-pending.jsonl")}, "source_verification": "Exact parents/subjects, all files/hunks applied to snapshots and MIT notices verified",
            "target_changes": 0, "training_approved": False, "research_run_authorized": False,
            "semantic_status": "Fixed training-only sample pending; no full semantic audit",
            "prior_sets": "Original 9758/962 and earlier 117-row CommitBench pilot stay separate and unchanged; no merged training export",
            "limitations": ["CC BY-NC commercial/distribution clearance unresolved", "Canonical/fork coverage incomplete",
                "Heuristic privacy screens incomplete", "Most subjects unreviewed", "Pretraining/copy overlap not exhaustively cleared"]}
        json_write(output / "manifest.json", manifest)
        check_protected(protected)
        report.update(status="target_reached" if len(accepted) == TARGET else "bounded_expansion_stopped",
            unattempted_selected_candidates=len(all_candidates)-attempted, accepted_repositories=len({row["repo_id"] for row in accepted}),
            pending_export_sha256=manifest["train"]["sha256"], manifest_sha256=file_sha(output / "manifest.json"),
            quality_sample_sha256=file_sha(output / "quality-sample.json"), protected_artifacts_unchanged=len(protected),
            dataset_targets_changed=0, source_seed_caches_preserved=True)
    except Exception as error:
        report.update(status="failed_preserve_artifacts", error=f"{type(error).__name__}: {error}")
        raise
    finally:
        report["finished_at_utc"] = dt.datetime.now(dt.UTC).isoformat()
        write_progress(output / "report.json", report)
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=Path(r"D:\PushTrackML"))
    run(parser.parse_args().workspace)
