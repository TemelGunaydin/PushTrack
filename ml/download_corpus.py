"""Download only pinned CommitChronicle train/validation shards on Windows."""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import threading

from prepare_pilot import DATASET, REVISION, Network, json_write, pinned_download

EXPECTED_BYTES = 12_205_933_927
EXPECTED_SHARDS = {"train": 61, "validation": 12}
EXPECTED_ROWS = {"train": 7_659_458, "validation": 1_554_042}


def selected_shards(tree):
    selected = []
    for entry in tree:
        match = re.fullmatch(r"data/(train|validation)-(\d{5})-of-(\d{5})-[a-f0-9]+\.parquet", entry["path"])
        if not match:
            continue  # Never acquire the test split or overlapping test subsets.
        split, number, count = match[1], int(match[2]), int(match[3])
        size, sha = entry["size"], entry["lfs"]["oid"]
        if count != EXPECTED_SHARDS[split] or not 0 < size <= 512_000_000 or not re.fullmatch(r"[a-f0-9]{64}", sha):
            raise ValueError("Unexpected pinned shard metadata")
        if entry["lfs"]["size"] != size:
            raise ValueError("Inconsistent LFS size")
        selected.append({"split": split, "number": number, "name": Path(entry["path"]).name,
                         "bytes": size, "sha256": sha, "path": entry["path"]})
    for split, count in EXPECTED_SHARDS.items():
        if sorted(s["number"] for s in selected if s["split"] == split) != list(range(count)):
            raise ValueError(f"Incomplete or duplicate {split} shard manifest")
    if sum(s["bytes"] for s in selected) != EXPECTED_BYTES:
        raise ValueError("Unexpected total download size at pinned revision")
    return sorted(selected, key=lambda s: (s["split"], s["number"]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=Path(r"D:\PushTrackML"))
    args = parser.parse_args()
    if platform.system() != "Windows":
        parser.error("Run corpus acquisition natively on Windows")
    root = args.workspace / "data" / "corpus-0001"
    tree = (root / "hub-tree.json").read_bytes()
    shards = selected_shards(json.loads(tree))
    destination = root / "shards"
    destination.mkdir(exist_ok=True)
    if shutil.disk_usage(root).free < EXPECTED_BYTES + 20_000_000_000:
        parser.error("Insufficient disk headroom for pinned shards and a 20 GB reserve")
    start = dt.datetime.now(dt.UTC)
    report = {"dataset": DATASET, "revision": REVISION, "started_at_utc": start.isoformat(),
              "manifest_sha256": hashlib.sha256(tree).hexdigest(), "expected_bytes": EXPECTED_BYTES,
              "test_acquired": False, "concurrency": 3, "status": "running", "files": []}
    stop = threading.Event()

    def obtain(row):
        if stop.is_set():
            return {**row, "status": "not_attempted"}
        network = Network(budget=row["bytes"])
        path = destination / row["name"]
        old = args.workspace / "data" / "pilot-0001" / row["name"]
        try:
            if not path.exists() and old.exists():
                with old.open("rb") as file:
                    sha = hashlib.file_digest(file, "sha256").hexdigest()
                if old.stat().st_size != row["bytes"] or sha != row["sha256"]:
                    raise ValueError("Existing pilot shard failed integrity")
                os.link(old, path)  # Both locations are immutable and on the same D: volume.
            pinned_download(network, path,
                            f'https://huggingface.co/datasets/{DATASET}/resolve/{REVISION}/{row["path"]}',
                            row["bytes"], row["sha256"])
            import pyarrow.parquet as pq
            return {**row, "status": "verified", "rows": pq.ParquetFile(path).metadata.num_rows,
                    "downloaded_bytes": network.received}
        except Exception as error:
            stop.set()  # No retries, alternate hosts, or quota bypass on any error.
            return {**row, "status": "failed", "error": f"{type(error).__name__}: {error}",
                    "downloaded_bytes": network.received}

    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = [pool.submit(obtain, row) for row in shards]
        for future in as_completed(futures):
            result = future.result()
            report["files"].append(result)
            done = sum(f["status"] == "verified" for f in report["files"])
            print(f'{done}/73 verified: {result["name"]} ({result["status"]})', flush=True)
    report["files"].sort(key=lambda row: (row["split"], row["number"]))
    report["downloaded_bytes"] = sum(row.get("downloaded_bytes", 0) for row in report["files"])
    report["rows"] = {split: sum(r.get("rows", 0) for r in report["files"] if r["split"] == split)
                      for split in EXPECTED_SHARDS}
    report["status"] = "complete" if all(r["status"] == "verified" for r in report["files"]) else "stopped"
    if report["status"] == "complete" and report["rows"] != EXPECTED_ROWS:
        report["status"] = "unexpected_row_counts"
    report["finished_at_utc"] = dt.datetime.now(dt.UTC).isoformat()
    records = root / "downloads"
    records.mkdir(exist_ok=True)
    name = start.strftime("%Y%m%dT%H%M%S%fZ")
    json_write(records / (name + ".json"), report)
    shutil.copyfile(Path(__file__), records / (name + ".py"))
    print(json.dumps({key: value for key, value in report.items() if key != "files"}, indent=2), flush=True)
    return 0 if report["status"] == "complete" else 1


if __name__ == "__main__":
    raise SystemExit(main())
