"""Batch-fetch original Git objects for a bounded, source-checked research set."""

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import sqlite3
import subprocess
import tempfile
import threading
import time
from urllib.parse import quote

from continue_pilot import OfficialTokenizer, screen_source_files
from prepare_corpus import GENERATED, write_progress
from prepare_pilot import DATASET, REVISION, PREFIX, Reject, StopCollection, digest, identity, safe_path, subject, validate_diff

LICENSE_NAMES = ("LICENSE", "LICENSE.txt", "LICENSE.md", "LICENSE.rst", "LICENCE", "COPYING", "LICENSE-MIT", "license", "license.txt", "license.md")
BINARY = re.compile(r"\.(?:png|jpe?g|gif|ico|pdf|zip|jar|exe|dll|so|bin|woff2?|ttf|mp[34]|wav|webp|parquet|pickle|pyc)$", re.I)
ZERO = "0" * 40
TARGETS = {"validation": 1000, "train": 10000}
PER_REPO = {"validation": 20, "train": 100}


def parse_commit(raw, expected_subject):
    try:
        header, body = raw.split(b"\n\n", 1)
        parents = [line.split()[1].decode("ascii") for line in header.splitlines() if line.startswith(b"parent ")]
        message = subject(body.decode("utf-8"))
    except (ValueError, UnicodeError, IndexError) as error:
        raise Reject("commit_encoding_or_subject") from error
    if len(parents) != 1 or not re.fullmatch(r"[a-f0-9]{40}", parents[0]):
        raise Reject("parent_count")
    if message != expected_subject:
        raise Reject("original_subject_mismatch")
    return parents[0], message


def parse_changes(raw):
    fields = raw.rstrip(b"\0").split(b"\0") if raw else []
    if len(fields) % 2 or not 1 <= len(fields) // 2 <= 5:
        raise Reject("original_file_count")
    result = []
    for index in range(0, len(fields), 2):
        metadata = fields[index].decode("ascii").split()
        path = fields[index + 1].decode("utf-8")
        if len(metadata) != 5 or not metadata[0].startswith(":"):
            raise Reject("git_raw_metadata")
        old_mode, new_mode, old_blob, new_blob, status = metadata
        old_mode = old_mode[1:]
        if old_mode not in ("000000", "100644", "100755") or new_mode not in ("000000", "100644", "100755"):
            raise Reject("symlink_submodule_or_mode")
        if status not in ("M", "A", "D") or not safe_path(path) or len(path) > 200:
            raise Reject("original_path_or_status")
        if GENERATED.search(path) or BINARY.search(path):
            raise Reject("original_generated_or_binary_path")
        if any(not re.fullmatch(r"[a-f0-9]{40}", value) for value in (old_blob, new_blob)):
            raise Reject("git_blob_identity")
        result.append({"filename": path, "status": {"M": "modified", "A": "added", "D": "removed"}[status],
                       "old_blob": old_blob, "new_blob": new_blob})
    return result


def license_paths(files):
    directories = {""}
    for file in files:
        parts = file["filename"].split("/")[:-1]
        if len(parts) > 8:
            raise Reject("license_path_depth")
        directories.update("/".join(parts[:i]) + "/" for i in range(1, len(parts) + 1))
    paths = sorted(prefix + name for prefix in directories for name in LICENSE_NAMES)
    if sum(len(p) + 3 for p in paths) > 18000:
        raise Reject("license_argument_budget")
    return paths


def parse_licenses(raw):
    result = {}
    for item in raw.split(b"\0"):
        if not item:
            continue
        meta, path = item.split(b"\t", 1)
        mode, kind, sha = meta.decode("ascii").split()
        path = path.decode("utf-8")
        if mode not in ("100644", "100755") or kind != "blob":
            raise Reject("non_regular_license")
        result[path] = sha
    if not any("/" not in path for path in result):
        raise Reject("missing_root_license")
    return result


def check_mit_notice(data):
    try:
        text = re.sub(r"\s+", " ", data.decode("utf-8-sig")).casefold()
    except UnicodeError as error:
        raise Reject("license_encoding") from error
    if not all(part in text for part in (
        "permission is hereby granted, free of charge", "the above copyright notice",
        "this permission notice shall be included", "the software is provided", "without warranty",
    )):
        raise Reject("non_standard_MIT_notice")
    if re.search(r"gnu (?:lesser |affero )?general public license|apache license|mozilla public license", text):
        raise Reject("conflicting_license_notice")


class GitSource:
    def __init__(self, directory, repo, temporary, stop, deadline=float("inf")):
        identity(repo, "a" * 40)
        self.directory, self.repo, self.temporary, self.stop = directory, repo, temporary, stop
        self.deadline = deadline
        self.env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        self.env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull, GIT_TERMINAL_PROMPT="0",
                        GCM_INTERACTIVE="Never", GIT_LFS_SKIP_SMUDGE="1", GIT_LITERAL_PATHSPECS="1",
                        TEMP=str(temporary), TMP=str(temporary))
        self.base = [shutil.which("git"), "--no-replace-objects", "-c", "core.hooksPath=NUL",
                     "-c", "core.fsmonitor=false", "-c", "gc.auto=0", "-c", "maintenance.auto=false",
                     "-c", "fetch.fsckObjects=true", "-c", "http.sslBackend=schannel", "-C", str(directory)]
        directory.mkdir(parents=True, exist_ok=False)
        self.run("init", "--bare")
        self.run("remote", "add", "origin", f"https://github.com/{repo}.git")
        self.blobs = {}

    def run(self, *args, data=None, limit=100_000, timeout=120):
        if self.stop.is_set() or time.monotonic() >= self.deadline:
            self.stop.set()
            raise StopCollection("Source run stopped or time budget reached")
        timeout = min(timeout, self.deadline - time.monotonic())
        # File-backed output avoids materializing an unexpectedly large Git blob.
        with tempfile.TemporaryFile(dir=self.temporary) as out, tempfile.TemporaryFile(dir=self.temporary) as err:
            process = subprocess.Popen(self.base + list(args), stdin=subprocess.PIPE if data is not None else subprocess.DEVNULL,
                                       stdout=out, stderr=err, env=self.env)
            try:
                process.communicate(data, timeout=timeout)
            except subprocess.TimeoutExpired:
                subprocess.run(["taskkill.exe", "/PID", str(process.pid), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                process.wait()
                if time.monotonic() >= self.deadline:
                    self.stop.set()
                    raise StopCollection("Source run time budget reached")
                raise Reject("git_timeout")
            err.seek(0)
            error = err.read(4000).decode("utf-8", errors="replace")
            if process.returncode:
                if re.search(r"\b403\b|\b429\b|rate limit|abuse detection", error, re.I):
                    self.stop.set()
                    raise StopCollection("Git server access/rate limit; no retry or alternate endpoint")
                raise Reject("git_unavailable_or_unsupported")
            size = out.tell()
            if size > limit:
                raise Reject("git_output_budget")
            out.seek(0)
            return out.read()

    def fetch(self, shas, commits=False):
        if any(not isinstance(sha, str) or not re.fullmatch(r"[a-f0-9]{40}", sha) for sha in shas):
            raise Reject("invalid_git_fetch_identity")
        for offset in range(0, len(shas), 96):
            args = ["fetch", "--quiet", "--no-tags", "--no-recurse-submodules", "--filter=blob:none"]
            if commits:
                args.append("--depth=2")
            self.run(*args, "origin", *shas[offset:offset + 96], timeout=180)
            if sum(p.stat().st_size for p in self.directory.rglob("*") if p.is_file()) > 256_000_000:
                raise Reject("repository_disk_budget")
            if shutil.disk_usage(self.directory).free < 20_000_000_000:
                self.stop.set()
                raise StopCollection("Workspace disk reserve reached")

    def blob(self, sha):
        if sha not in self.blobs:
            data = self.run("cat-file", "blob", sha, limit=200_000)
            actual = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
            if actual != sha:
                raise StopCollection("Original Git blob integrity failed")
            self.blobs[sha] = data
        return self.blobs[sha]


def build_plan(git, candidate):
    sha = candidate["commit_id"]
    parent, message = parse_commit(git.run("cat-file", "commit", sha, limit=20000), candidate["subject"])
    files = parse_changes(git.run("diff-tree", "--no-commit-id", "--raw", "-r", "-z", "--no-renames", "--no-abbrev", parent, sha))
    paths = license_paths(files)
    notices = {revision: parse_licenses(git.run("ls-tree", "-r", "-z", revision, "--", *paths)) for revision in (parent, sha)}
    return {"candidate": candidate, "parent": parent, "message": message, "files": files, "notices": notices}


def materialize(git, plan, tokenizer, output):
    candidate, parent, files = plan["candidate"], plan["parent"], plan["files"]
    sha = candidate["commit_id"]
    notices = []
    for revision, paths in plan["notices"].items():
        for path, blob in paths.items():
            content = git.blob(blob)
            check_mit_notice(content)
            fingerprint = digest(content)
            (output / "licenses" / (fingerprint + ".txt")).write_bytes(content)
            notices.append({"revision": revision, "path": path, "blob_sha": blob, "sha256": fingerprint})
    patch = git.run("diff", "--no-ext-diff", "--no-textconv", "--no-renames", "--no-color", "--abbrev=8", parent, sha, "--")
    try:
        diff = patch.decode("utf-8")
    except UnicodeError as error:
        raise Reject("original_diff_encoding") from error
    stats = git.run("diff", "--no-ext-diff", "--no-textconv", "--no-renames", "--numstat", "-z", parent, sha, "--")
    by_path = {f["filename"]: f for f in files}
    for entry in stats.split(b"\0"):
        if not entry:
            continue
        additions, deletions, path = entry.decode("utf-8").split("\t", 2)
        if not additions.isdigit() or not deletions.isdigit() or path not in by_path:
            raise Reject("original_binary_or_stats")
        by_path[path].update(additions=int(additions), deletions=int(deletions))
    if any("additions" not in f for f in files):
        raise Reject("missing_original_stats")
    validate_diff(diff, {"files": files, "stats": {key: sum(f[key] for f in files) for key in ("additions", "deletions")}})
    inputs, targets = len(tokenizer.encode(PREFIX + diff).ids), len(tokenizer.encode(plan["message"]).ids)
    if inputs > 512 or targets > 64:
        raise Reject("full_diff_token_budget")
    snapshots = []
    for revision, side in ((parent, "old_blob"), (sha, "new_blob")):
        mapping = {f'https://raw.githubusercontent.com/{git.repo}/{revision}/{quote(f["filename"], safe="/")}': f[side]
                   for f in files if f[side] != ZERO}
        class LocalBlobs:
            def fetch(self, url, limit):
                return git.blob(mapping[url]), {}
        row = {"repo_id": git.repo, "commit_id": revision, "files": [f["filename"] for f in files if f[side] != ZERO]}
        screen_source_files(LocalBlobs(), row, output / "source-files")
        for evidence in row["source_file_screening"]:
            evidence["blob_sha"] = mapping[evidence["url"]]
            snapshots.append(evidence)
    patch_id = git.run("patch-id", "--stable", data=patch, limit=1024).split()[0].decode("ascii")
    if not re.fullmatch(r"[a-f0-9]{40}", patch_id):
        raise Reject("invalid_patch_id")
    return {"schema_version": 1, "repo_id": git.repo, "commit_id": sha, "parent_id": parent, "split": candidate["split"],
            "diff": diff, "diff_sha256": digest(patch), "patch_id": patch_id, "message": plan["message"],
            "files": [f["filename"] for f in files], "input_tokens": inputs, "target_tokens": targets,
            "source": {"kind": "git", "url": f"https://github.com/{git.repo}/commit/{sha}", "license": "MIT",
                       "method": "bare Git, exact commit and parent, no checkout", "license_evidence": notices},
            "source_file_screening": snapshots,
            "dataset": {"name": DATASET, "revision": REVISION, "shard": candidate["shard"], "row_index": candidate["row_index"]},
            "review_status": "source_checked_pending_quality_review", "training_approved": False,
            "target_origin": "original commit subject; English/action heuristics only"}


def verify_repository(job, workspace, output, stop, deadline=float("inf")):
    repo, split, candidates = job
    result = {"repo_id": repo, "split": split, "rows": [], "rejections": Counter(), "status": "complete"}
    path = output / "repos" / hashlib.sha256(repo.encode()).hexdigest()[:24]
    try:
        git = GitSource(path, repo, workspace / ".tmp", stop, deadline)
        git.fetch([r["commit_id"] for r in candidates], commits=True)
        plans, blobs = [], set()
        for candidate in candidates:
            try:
                plan = build_plan(git, candidate)
                plans.append(plan)
                blobs.update(blob for f in plan["files"] for blob in (f["old_blob"], f["new_blob"]) if blob != ZERO)
                blobs.update(blob for paths in plan["notices"].values() for blob in paths.values())
            except (Reject, UnicodeError) as error:
                result["rejections"][str(error) if isinstance(error, Reject) else "source_encoding"] += 1
        git.fetch(sorted(blobs))
        tokenizer = OfficialTokenizer(workspace / "runs" / "tokenizer-0002" / "codet5-small")
        for plan in plans:
            try:
                result["rows"].append(materialize(git, plan, tokenizer, output))
            except (Reject, UnicodeError) as error:
                result["rejections"][str(error) if isinstance(error, Reject) else "source_encoding"] += 1
            if len(result["rows"]) >= PER_REPO[split]:
                break
    except StopCollection as error:
        stop.set()
        result.update(status="stopped", error=str(error))
    except Exception as error:
        result.update(status="repository_failed", error=f"{type(error).__name__}: {error}")
    result["stored_git_bytes"] = sum(p.stat().st_size for p in path.rglob("*") if p.is_file()) if path.exists() else 0
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=Path(r"D:\PushTrackML"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if platform.system() != "Windows":
        parser.error("Run source preparation natively on Windows")
    if args.output.exists():
        parser.error("Preserve existing source-check evidence; output must be new")
    root = args.workspace / "data" / "corpus-0001" / "prepared"
    preparation = json.loads((root / "report.json").read_text())
    if preparation["status"] != "complete_candidate_preparation":
        parser.error("Candidate preparation is not complete")
    for name in ("TEMP", "TMP", "SQLITE_TMPDIR"):
        os.environ[name] = str(args.workspace / ".tmp")
    os.environ["HF_HOME"] = str(args.workspace / ".cache" / "huggingface")
    args.output.mkdir(parents=True)
    for name in ("licenses", "source-files", "repos", "provenance"):
        (args.output / name).mkdir()
    for name in ("verify_corpus_sources.py", "prepare_corpus.py", "download_corpus.py", "continue_pilot.py", "compare_tokenizers.py", "prepare_pilot.py", "requirements-data.lock"):
        shutil.copyfile(Path(__file__).parent / name, args.output / "provenance" / name)
    connection = sqlite3.connect(f"{(root / 'candidates.sqlite3').as_uri()}?mode=ro", uri=True)
    report = {"status": "running", "started_at_utc": dt.datetime.now(dt.UTC).isoformat(),
              "targets": TARGETS, "accepted": {"train": 0, "validation": 0}, "repositories_checked": 0,
              "rejections": {}, "git_storage_bytes": 0, "training_approved": False,
              "scope": "source-checked automatic screening; quality/fork-family review remains required",
              "fork_check": "Selected commit/parent overlap only; not an exhaustive family audit",
              "budgets": {"seconds": 7200, "git_storage_threshold_bytes": 8_000_000_000,
                          "per_repository_git_bytes": 256_000_000, "parallel_repositories": 2},
              "test_read": False, "source_sha256": digest(Path(__file__).read_bytes()),
              "candidate_report_sha256": digest((root / "report.json").read_bytes())}
    stop = threading.Event()
    seen_patches, validation_objects, rejected = set(), set(), Counter()
    deadline = time.monotonic() + 7200
    try:
        with (args.output / "repositories.jsonl").open("x", encoding="utf-8") as repo_log:
            for split in ("validation", "train"):
                repositories = [r[0] for r in connection.execute("SELECT repo_id FROM candidates WHERE split=? GROUP BY repo_id HAVING COUNT(*)>=8", (split,))]
                repositories.sort(key=lambda repo: hashlib.sha256(("42:" + repo).encode()).hexdigest())
                with (args.output / (split + "-pending.jsonl")).open("x", encoding="utf-8", newline="\n") as rows_file:
                    for offset in range(0, len(repositories), 2):
                        if stop.is_set() or report["accepted"][split] >= TARGETS[split] or time.monotonic() > deadline:
                            break
                        jobs = []
                        for repo in repositories[offset:offset + 2]:
                            candidates = [dict(zip(("commit_id", "shard", "row_index", "subject"), row), split=split)
                                          for row in connection.execute("SELECT commit_id,shard,row_index,subject FROM candidates WHERE split=? AND repo_id=? ORDER BY priority LIMIT ?", (split, repo, 64 if split == "validation" else 192))]
                            jobs.append((repo, split, candidates))
                        with ThreadPoolExecutor(max_workers=2) as pool:
                            results = list(pool.map(lambda job: verify_repository(job, args.workspace, args.output, stop, deadline), jobs))
                        for result in results:
                            rows = result.pop("rows")
                            report["repositories_checked"] += 1
                            report["git_storage_bytes"] += result["stored_git_bytes"]
                            rejected.update(result["rejections"])
                            shared = {object_id for row in rows for object_id in (row["commit_id"], row["parent_id"])} & validation_objects
                            for row in rows:
                                if split == "train" and shared:
                                    rejected["shared_validation_commit_family"] += 1
                                    continue
                                if row["patch_id"] in seen_patches:
                                    rejected["duplicate_stable_patch"] += 1
                                    continue
                                if report["accepted"][split] >= TARGETS[split]:
                                    break
                                seen_patches.add(row["patch_id"])
                                if split == "validation":
                                    validation_objects.update((row["commit_id"], row["parent_id"]))
                                rows_file.write(json.dumps(row, ensure_ascii=True) + "\n")
                                report["accepted"][split] += 1
                            rows_file.flush()
                            repo_log.write(json.dumps(result, ensure_ascii=True) + "\n")
                            repo_log.flush()
                            report["rejections"] = dict(rejected)
                            write_progress(args.output / "report.json", report)
                            print(f'{split}: {report["accepted"][split]:,}/{TARGETS[split]:,} source-checked; {result["repo_id"]}: {result["status"]}', flush=True)
                        if report["git_storage_bytes"] >= 8_000_000_000:
                            stop.set()
        report["status"] = "targets_reached" if report["accepted"] == TARGETS else "bounded_pass_stopped"
    except Exception as error:
        report.update(status="failed", error=f"{type(error).__name__}: {error}")
        raise
    finally:
        connection.close()
        report["finished_at_utc"] = dt.datetime.now(dt.UTC).isoformat()
        write_progress(args.output / "report.json", report)
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
