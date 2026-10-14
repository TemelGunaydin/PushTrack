"""Offline regression tests: synthetic fixtures only; requires the data environment."""

import base64
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import prepare_pilot as pilot

PATCH = """diff --git a/main.py b/main.py
index 0000001..0000002 100644
--- a/main.py
+++ b/main.py
@@ -1,2 +1,2 @@
 def answer():
-    return 0
+    return 42
"""
COMMIT_ID = "a" * 40
PARENT_ID = "b" * 40


def commit_info():
    return {
        "sha": COMMIT_ID,
        "parents": [{"sha": PARENT_ID}],
        "commit": {"message": "Return the expected answer"},
        "files": [{"filename": "main.py", "status": "modified", "additions": 1, "deletions": 1}],
        "stats": {"additions": 1, "deletions": 1},
    }


class FakeTokenizer:
    def __init__(self, count=10):
        self.ids = list(range(count))
        self.texts = []

    def encode(self, text):
        self.texts.append(text)
        return self


class FakeNetwork:
    def __init__(self):
        self.info = commit_info()
        self.headers = {}
        self.requests = []
        self.patch = PATCH
        self.notice = b"Permission is hereby granted, free of charge\nTHE SOFTWARE IS PROVIDED\n"
        blob = b"blob " + str(len(self.notice)).encode() + b"\0" + self.notice
        self.license = {
            "license": {"spdx_id": "MIT"}, "encoding": "base64",
            "content": base64.b64encode(self.notice).decode(),
            "path": "LICENSE", "sha": hashlib.sha1(blob).hexdigest(),
        }

    def json(self, url, limit=2_000_000):
        self.requests.append(url)
        return (self.license, {}) if "/license?" in url else (self.info, self.headers)

    def fetch(self, url, limit):
        self.requests.append(url)
        return self.patch.encode(), {}


class DataPolicyTests(unittest.TestCase):
    def test_identity_rejects_url_injection_and_invalid_commit(self):
        pilot.identity("owner/repo", COMMIT_ID)
        for repo, sha in [("../repo", COMMIT_ID), ("owner/repo?x=1", COMMIT_ID), ("owner/repo", "main")]:
            with self.subTest(repo=repo, sha=sha), self.assertRaises(pilot.Reject):
                pilot.identity(repo, sha)

    def test_paths(self):
        self.assertTrue(pilot.safe_path("src/main.py"))
        for path in ["../main.py", "/root/file", "a//b", "a/./b", "C:\\x", "file with spaces"]:
            self.assertFalse(pilot.safe_path(path), path)

    def test_subject_preserves_first_line_without_inventing_a_prefix(self):
        self.assertEqual(pilot.subject("Return the expected answer\n\nDetails"), "Return the expected answer")

    def test_subject_rejections(self):
        for text in ["", "fix", "wip: finish the change", "Fix issue #123", "a " * 40, "Update the café name", "Fix\x1b[0m the output"]:
            with self.subTest(text=text), self.assertRaises(pilot.Reject):
                pilot.subject(text)

    def test_complete_patch(self):
        pilot.validate_diff(PATCH, commit_info())

    def test_truncated_patch_is_rejected(self):
        with self.assertRaisesRegex(pilot.Reject, "incomplete_hunk"):
            pilot.validate_diff(PATCH.replace("+    return 42\n", ""), commit_info())

    def test_hunk_overflow_is_rejected(self):
        with self.assertRaisesRegex(pilot.Reject, "hunk_count_mismatch"):
            pilot.validate_diff(PATCH + "+extra\n", commit_info())

    def test_two_files_keep_complete_commit(self):
        info = commit_info()
        info["files"].append({"filename": "test.py", "status": "modified", "additions": 1, "deletions": 1})
        info["stats"] = {"additions": 2, "deletions": 2}
        pilot.validate_diff(PATCH + PATCH.replace("main.py", "test.py"), info)
        with self.assertRaisesRegex(pilot.Reject, "diff_file_count_mismatch"):
            pilot.validate_diff(PATCH, info)

    def test_addition_and_deletion(self):
        addition = "diff --git a/a.py b/a.py\nnew file mode 100644\n--- /dev/null\n+++ b/a.py\n@@ -0,0 +1 @@\n+x = 1\n"
        deletion = "diff --git a/b.py b/b.py\ndeleted file mode 100644\n--- a/b.py\n+++ /dev/null\n@@ -1 +0,0 @@\n-x = 2\n"
        info = {"files": [
            {"filename": "a.py", "status": "added", "additions": 1, "deletions": 0},
            {"filename": "b.py", "status": "removed", "additions": 0, "deletions": 1},
        ], "stats": {"additions": 1, "deletions": 1}}
        pilot.validate_diff(addition + deletion, info)

    def test_no_final_newline_marker(self):
        pilot.validate_diff(PATCH.rstrip("\n") + "\n\\ No newline at end of file\n", commit_info())

    def test_binary_and_secret_rejections(self):
        for marker in ["Binary files a/main.py and b/main.py differ", "GIT binary patch", "Subproject commit abc", "-----BEGIN PRIVATE KEY-----", 'api_key = "abcdefghijklmnop"']:
            with self.subTest(marker=marker), self.assertRaises(pilot.Reject):
                pilot.validate_diff(PATCH + marker, commit_info())

    def test_stats_mismatch(self):
        info = commit_info()
        info["files"][0]["additions"] = 2
        with self.assertRaisesRegex(pilot.Reject, "diff_stats_mismatch"):
            pilot.validate_diff(PATCH, info)

    def test_generated_and_unsupported_paths(self):
        for name in ["vendor/main.py", "package-lock.json", "a b.py"]:
            info = commit_info()
            info["files"][0]["filename"] = name
            with self.subTest(name=name), self.assertRaises(pilot.Reject):
                pilot.validate_diff(PATCH.replace("main.py", name), info)

    def test_license_at_original_revision_and_pending_review(self):
        network, tokenizer = FakeNetwork(), FakeTokenizer()
        with tempfile.TemporaryDirectory() as directory:
            row = pilot.verify_row(network, {"repo_id": "owner/repo", "commit_id": COMMIT_ID, "split": "train"}, tokenizer, Path(directory))
            self.assertEqual(row["review_status"], "pending")
            self.assertEqual(row["parent_id"], PARENT_ID)
            self.assertEqual(row["source"]["license"], "MIT")
            self.assertEqual(row["diff"], PATCH)
            self.assertEqual(tokenizer.texts, [pilot.PREFIX + PATCH, "Return the expected answer"])
            self.assertIn("/license?ref=" + COMMIT_ID, network.requests[-1])
            self.assertEqual(len(list(Path(directory).glob("*.txt"))), 1)

    def test_token_budget_never_truncates(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(pilot.Reject, "token_budget"):
                pilot.verify_row(FakeNetwork(), {"repo_id": "owner/repo", "commit_id": COMMIT_ID, "split": "train"}, FakeTokenizer(513), Path(directory))
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_paginated_commit_and_merge_fail_closed(self):
        for mode in ["paginated", "merge"]:
            network = FakeNetwork()
            if mode == "paginated":
                network.headers = {"Link": '<https://api.github.com/page2>; rel="next"'}
            else:
                network.info["parents"].append({"sha": "c" * 40})
            with tempfile.TemporaryDirectory() as directory, self.subTest(mode=mode), self.assertRaises(pilot.Reject):
                pilot.verify_row(network, {"repo_id": "owner/repo", "commit_id": COMMIT_ID, "split": "train"}, FakeTokenizer(), Path(directory))

    def test_wrong_license_and_corrupt_notice(self):
        for mode in ["other_license", "corruption"]:
            network = FakeNetwork()
            if mode == "other_license":
                network.license["license"]["spdx_id"] = "GPL-3.0"
            else:
                network.license["sha"] = "0" * 40
            with tempfile.TemporaryDirectory() as directory, self.subTest(mode=mode), self.assertRaises(pilot.Reject):
                pilot.verify_row(network, {"repo_id": "owner/repo", "commit_id": COMMIT_ID, "split": "train"}, FakeTokenizer(), Path(directory))

    def test_corrupt_existing_download_not_silently_replaced(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample"
            path.write_bytes(b"corrupted")
            with self.assertRaisesRegex(pilot.StopCollection, "integrity"):
                pilot.pinned_download(None, path, "unused", 9, "0" * 64)
            self.assertEqual(path.read_bytes(), b"corrupted")

    def test_valid_pinned_file_does_not_need_network(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample"
            path.write_bytes(b"fixture")
            pilot.pinned_download(None, path, "unused", 7, pilot.digest(b"fixture"))

    def test_candidates_enforce_caps_and_case_insensitive_project_splits(self):
        import pyarrow as pa
        import pyarrow.parquet as pq

        def fixture(repo, index, license_name="MIT License"):
            return {"repo": repo, "hash": f"{index:040x}", "license": license_name,
                    "message": "Return the expected answer", "mods": [{"diff": "-0\n+42\n"}]}

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            train = [fixture("Owner/Repo", i) for i in range(30)]
            train += [fixture("other/repo", 99, "Apache License 2.0")]
            validation = [fixture("owner/repo", 100), fixture("separate/repo", 101)]
            for split, rows in [("train", train), ("validation", validation)]:
                pq.write_table(pa.Table.from_pylist(rows), root / pilot.SHARDS[split][0])
            rows, report = pilot.candidates(root)
            self.assertEqual(report["train"]["selected"], 20)
            self.assertEqual(report["train"]["rejections"]["per_repository_cap"], 10)
            self.assertEqual(report["validation"]["selected"], 1)
            self.assertEqual(report["validation"]["rejections"]["duplicate_or_split_overlap"], 1)
            self.assertEqual(rows[-1]["repo_id"], "separate/repo")
            self.assertEqual(pilot.candidates(root), (rows, report))

    def test_rate_limit_stops_before_network_call(self):
        network = pilot.Network()
        network.remaining = 5
        with patch.object(pilot, "urlopen") as request, self.assertRaises(pilot.StopCollection):
            network.fetch("https://api.github.com/repos/owner/repo", 1000)
        request.assert_not_called()


if __name__ == "__main__":
    unittest.main()
