"""Offline synthetic checks for large-corpus filtering; no real data/network."""
from collections import Counter
import copy
import sqlite3
import unittest

from prepare_corpus import inspect_candidate, flush_batch
from prepare_pilot import Reject


class CorpusPreparationTests(unittest.TestCase):
    def row(self):
        return {"repo": "Owner/Repo", "hash": "a" * 40, "license": "MIT License",
                "original_message": "Fix the missing return value", "message": "different processed message",
                "language": "Python", "mods": [{"change_type": "MODIFY", "old_path": "main.py", "new_path": "main.py", "diff": "-return 0\n+return value\n"}]}

    def test_preserves_original_subject_and_marks_representation(self):
        candidate = inspect_candidate(self.row())
        self.assertEqual(candidate["subject"], "Fix the missing return value")
        self.assertEqual(candidate["repo_id"], "owner/repo")
        self.assertIn("processed_mods", candidate)
        self.assertNotIn("diff", candidate)
        self.assertNotIn(candidate["subject"], candidate["estimate_text"])

    def test_declared_license_and_generic_subject_filters(self):
        for key, value in (("license", "GNU GPL"), ("original_message", "Update some changes"),
                           ("original_message", "Arreglar un problema"), ("original_message", "Fix issue #123 today")):
            row = self.row()
            row[key] = value
            with self.assertRaises(Reject):
                inspect_candidate(row)

    def test_whole_example_rejected_for_vendor_or_rename(self):
        row = self.row()
        row["mods"].append({"change_type": "MODIFY", "old_path": "vendor/a.py", "new_path": "vendor/a.py", "diff": "-1\n+2"})
        with self.assertRaisesRegex(Reject, "generated_path"):
            inspect_candidate(row)
        row = self.row()
        row["mods"][0]["new_path"] = "renamed.py"
        with self.assertRaisesRegex(Reject, "rename"):
            inspect_candidate(row)

    def test_secrets_controls_and_missing_modifications_rejected(self):
        for diff in ("+api_key = 'abcdefghijklmnop'", "+bad\x00text", "+bad\x7ftext", None):
            row = self.row()
            row["mods"][0]["diff"] = diff
            with self.assertRaises(Reject):
                inspect_candidate(row)
        row["mods"] = [None]
        with self.assertRaises(Reject):
            inspect_candidate(row)

    def database(self):
        connection = sqlite3.connect(":memory:")
        connection.execute("CREATE TABLE candidates (commit_id TEXT PRIMARY KEY,repo_id,split,shard,row_index,subject,language,processed_mods,processed_hash TEXT UNIQUE,processed_tokens,target_tokens,priority)")
        self.addCleanup(connection.close)
        return connection

    def candidate(self, split="validation"):
        row = inspect_candidate(self.row())
        row.update(split=split, shard="fixture.parquet", row_index=0)
        return row

    def test_duplicate_processed_patch_cannot_cross_splits(self):
        connection = self.database()
        rejected = Counter()
        def tokenizer(texts, **kwargs):
            self.assertFalse(kwargs["truncation"])
            self.assertFalse(kwargs["padding"])
            return {"input_ids": [[1, 7, 2] for _ in texts]}
        self.assertEqual(flush_batch(connection, [self.candidate()], tokenizer, {0, 1, 2}, rejected), 1)
        duplicate = self.candidate("train")
        duplicate["commit_id"] = "b" * 40
        self.assertEqual(flush_batch(connection, [duplicate], tokenizer, {0, 1, 2}, rejected), 0)
        self.assertEqual(rejected["duplicate_commit_or_processed_patch"], 1)
        self.assertEqual(connection.execute("SELECT split FROM candidates").fetchall(), [("validation",)])

    def test_oversized_or_reserved_inputs_are_not_saved(self):
        for ids in ([1] + [7] * 511 + [2], [1, 99, 2]):
            connection = self.database()
            rejected = Counter()
            def tokenizer(texts, **kwargs):
                return {"input_ids": [ids, [1, 7, 2]]}
            self.assertEqual(flush_batch(connection, [self.candidate()], tokenizer, {0, 1, 2, 99}, rejected), 0)
            self.assertEqual(sum(rejected.values()), 1)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM candidates").fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()
