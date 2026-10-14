"""Small offline regressions for manifest continuation and conservative screening."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from continue_pilot import OfficialTokenizer, choose_candidates, screen_source_files
from prepare_pilot import Reject


class ContinuationTests(unittest.TestCase):
    def row(self, index, split="train"):
        return {"repo_id": f"owner/repo{index}", "commit_id": f"{index:040x}", "split": split}

    def test_skips_completed_but_retries_old_token_budget(self):
        candidates = [self.row(i) for i in range(6)]
        rejections = [{**self.row(1), "reason": "http_404"}, {**self.row(2), "reason": "token_budget"}]
        chosen = choose_candidates(candidates, [self.row(0)], rejections)
        self.assertEqual([row["commit_id"] for row in chosen], [self.row(i)["commit_id"] for i in (2, 3, 4, 5)])

    def test_interleaves_validation_and_bounds_attempts(self):
        candidates = [self.row(i) for i in range(100)] + [self.row(i, "validation") for i in range(100, 120)]
        chosen = choose_candidates(candidates, [], [])
        self.assertEqual(len(chosen), 40)
        self.assertEqual([r["split"] for r in chosen[:4]], ["train", "train", "train", "validation"])

    def test_literal_specials_rejected_before_tokenization(self):
        adapter = OfficialTokenizer.__new__(OfficialTokenizer)
        adapter.tokenizer = Mock()
        adapter.tokenizer.all_special_tokens = ["<mask>"]
        with self.assertRaisesRegex(Reject, "literal_special_marker"):
            adapter.encode('value = "  <mask>"')
        adapter.tokenizer.encode.assert_not_called()

    def test_source_notice_conflicts_rejected_without_storage(self):
        for content in [b"# SPDX-License-Identifier: GPL-3.0\n", b"# Apache License\n", b'api_key = "abcdefghijklmnop"']:
            network = SimpleNamespace(fetch=lambda *args: (content, {}))
            row = {**self.row(1), "files": ["main.py"]}
            with tempfile.TemporaryDirectory() as directory:
                with self.assertRaises(Reject):
                    screen_source_files(network, row, Path(directory))
                self.assertEqual(list(Path(directory).iterdir()), [])

    def test_source_bytes_and_provenance_preserved(self):
        content = b"# SPDX-License-Identifier: MIT\nreturn_value = 1\n"
        network = SimpleNamespace(fetch=lambda *args: (content, {}))
        row = {**self.row(1), "files": ["main.py"]}
        with tempfile.TemporaryDirectory() as directory:
            screen_source_files(network, row, Path(directory))
            evidence = row["source_file_screening"][0]
            self.assertEqual((Path(directory) / (evidence["sha256"] + ".txt")).read_bytes(), content)
            self.assertEqual(evidence["revision"], row["commit_id"])


if __name__ == "__main__":
    unittest.main()
