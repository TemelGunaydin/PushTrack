"""Local synthetic Git tests; no network or real source acquisition."""
from pathlib import Path
import tempfile
import threading
import unittest

from prepare_pilot import Reject, StopCollection
from verify_corpus_sources import GitSource, check_mit_notice, license_paths, parse_changes, parse_commit, parse_licenses


class SourceTests(unittest.TestCase):
    def test_original_subject_and_single_parent_required(self):
        parent = "b" * 40
        raw = (f"tree {'a'*40}\nparent {parent}\n\nFix the missing return value\n").encode()
        self.assertEqual(parse_commit(raw, "Fix the missing return value"), (parent, "Fix the missing return value"))
        with self.assertRaisesRegex(Reject, "subject_mismatch"):
            parse_commit(raw, "Remove the return value")
        with self.assertRaisesRegex(Reject, "parent_count"):
            parse_commit(raw.replace(b"\n\n", (f"\nparent {'c'*40}\n\n").encode()), "Fix the missing return value")

    def test_full_file_list_and_modes(self):
        data = (f":100644 100755 {'a'*40} {'b'*40} M\0src/main.py\0").encode()
        files = parse_changes(data)
        self.assertEqual(files[0]["filename"], "src/main.py")
        self.assertEqual(files[0]["status"], "modified")
        for bad in (data.replace(b"100644", b"160000"), data.replace(b"src/main.py", b"../secret"),
                    data.replace(b"src/main.py", b"assets/icon.png"), data * 6):
            with self.assertRaises(Reject):
                parse_changes(bad)

    def test_missing_or_symbolic_root_notice_rejected(self):
        raw = (f"100644 blob {'a'*40}\tLICENSE\0").encode()
        self.assertEqual(parse_licenses(raw), {"LICENSE": "a" * 40})
        with self.assertRaisesRegex(Reject, "missing_root"):
            parse_licenses(raw.replace(b"LICENSE", b"src/LICENSE"))
        with self.assertRaisesRegex(Reject, "non_regular"):
            parse_licenses(raw.replace(b"100644", b"120000"))

    def test_nested_licenses_are_not_ignored(self):
        paths = license_paths([{"filename": "src/component/main.py"}])
        self.assertIn("LICENSE", paths)
        self.assertIn("src/LICENSE", paths)
        self.assertIn("src/component/LICENSE", paths)

    def test_notice_requires_mit_terms_and_rejects_conflicts(self):
        notice = b'Permission is hereby granted, free of charge. The above copyright notice and this permission notice shall be included. THE SOFTWARE IS PROVIDED WITHOUT WARRANTY.'
        check_mit_notice(notice)
        with self.assertRaises(Reject):
            check_mit_notice(b"MIT")
        with self.assertRaisesRegex(Reject, "conflicting"):
            check_mit_notice(notice + b" Apache License")

    def test_expired_run_starts_no_git_command(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stop = threading.Event()
            with self.assertRaises(StopCollection):
                GitSource(root / "expired.git", "owner/repo", root, stop, deadline=0)
            self.assertTrue(stop.is_set())
            self.assertFalse((root / "expired.git" / "HEAD").exists())

    def test_bare_git_blob_identity_and_output_budget(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            git = GitSource(root / "objects.git", "owner/repo", root, threading.Event())
            data = b"synthetic source only\n"
            sha = git.run("hash-object", "-w", "--stdin", data=data).decode().strip()
            self.assertEqual(git.blob(sha), data)
            too_large = git.run("hash-object", "-w", "--stdin", data=b"x" * 200001).decode().strip()
            with self.assertRaisesRegex(Reject, "output_budget"):
                git.blob(too_large)
            with self.assertRaisesRegex(Reject, "fetch_identity"):
                git.fetch(["--upload-pack=untrusted"])


if __name__ == "__main__":
    unittest.main()
