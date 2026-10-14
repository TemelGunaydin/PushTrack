"""Offline tokenizer-metric regressions with tiny synthetic vocabularies."""

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from tokenizers import Tokenizer, models, pre_tokenizers, processors

import compare_tokenizers as comparison


class TokenizerMetricTests(unittest.TestCase):
    def backend(self):
        backend = Tokenizer(models.WordLevel({"<unk>": 0, "a": 1, "b": 2}, unk_token="<unk>"))
        backend.pre_tokenizer = pre_tokenizers.Whitespace()
        return backend

    def test_exact_roundtrip(self):
        result = comparison.measure(self.backend(), "a b", "<unk>")
        self.assertTrue(result["exact_roundtrip"])
        self.assertEqual(result["unknown_id_occurrences"], 0)
        self.assertEqual(result["tokens_with_specials"], 2)

    def test_zero_unknown_tokens_does_not_prove_fidelity(self):
        result = comparison.measure(self.backend(), "a\n\tb", "<unk>")
        self.assertEqual(result["unknown_id_occurrences"], 0)
        self.assertFalse(result["exact_roundtrip"])
        self.assertFalse(result["newlines_preserved"])
        self.assertFalse(result["tabs_preserved"])

    def test_unknown_tokens_are_counted(self):
        result = comparison.measure(self.backend(), "a missing", "<unk>")
        self.assertEqual(result["unknown_id_occurrences"], 1)
        self.assertFalse(result["exact_roundtrip"])

    def test_inserted_special_tokens_do_not_inflate_unknown_count(self):
        backend = self.backend()
        backend.post_processor = processors.TemplateProcessing(
            single="<unk> $A <unk>", special_tokens=[("<unk>", 0)]
        )
        result = comparison.measure(backend, "a b", "<unk>")
        self.assertEqual(result["tokens_with_specials"], 4)
        self.assertEqual(result["unknown_id_occurrences"], 0)
        self.assertTrue(result["exact_roundtrip"])

    def test_no_unknown_id_is_not_an_exception(self):
        self.assertEqual(comparison.measure(self.backend(), "a", "not-a-token")["unknown_id_occurrences"], 0)

    def test_artifact_checks_size_and_git_blob_hash(self):
        content = b"synthetic asset"
        blob = hashlib.sha1(b"blob 15\0" + content).hexdigest()
        self.assertEqual(comparison.verify_asset(content, 15, blob), hashlib.sha256(content).hexdigest())
        for size, sha in [(16, blob), (15, "0" * 40)]:
            with self.subTest(size=size, sha=sha), self.assertRaises(ValueError):
                comparison.verify_asset(content, size, sha)

    def test_download_allowlist_excludes_model_weights_and_remote_code(self):
        allowed = {"README.md", "config.json", "tokenizer_config.json", "special_tokens_map.json", "added_tokens.json", "vocab.json", "merges.txt", "tokenizer.json"}
        total = 0
        for candidate in comparison.CANDIDATES.values():
            self.assertEqual(len(candidate["revision"]), 40)
            self.assertTrue(set(candidate["files"]).issubset(allowed))
            total += sum(size for size, _ in candidate["files"].values())
        self.assertLess(total, 6_000_000)

    def test_codet5_backend_reconstruction_keeps_special_ids_and_bytes(self):
        vocabulary = {token: index for index, token in enumerate(["<pad>", "<s>", "</s>", "<unk>"] + sorted(pre_tokenizers.ByteLevel.alphabet()))}
        special = {role: {"content": token, "normalized": True, "single_word": False, "lstrip": False, "rstrip": False}
                   for role, token in [("bos_token", "<s>"), ("eos_token", "</s>"), ("unk_token", "<unk>"), ("pad_token", "<pad>")]}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, value in {
                "vocab.json": vocabulary,
                "tokenizer_config.json": {"add_prefix_space": False},
                "special_tokens_map.json": special,
                "added_tokens.json": {},
                "config.json": {"bos_token_id": 1, "eos_token_id": 2, "vocab_size": len(vocabulary)},
            }.items():
                (root / name).write_text(json.dumps(value), encoding="utf-8")
            (root / "merges.txt").write_text("#version: 0.2\n", encoding="utf-8")
            backend = comparison.load_codet5(root)
            self.assertEqual(backend.encode("a").ids, [1, vocabulary["a"], 2])
            self.assertTrue(comparison.measure(backend, "{\n\t café = 1;\n}", "<unk>")["exact_roundtrip"])

    def test_comparison_disables_existing_truncation(self):
        backend = self.backend()
        backend.enable_truncation(1)
        diff = "a b"
        rows = [{"diff": diff, "diff_sha256": comparison.digest(diff.encode()), "message": "a b", "split": "train"}]
        result = comparison.compare(backend, rows, "<unk>")
        self.assertIsNone(backend.truncation)
        self.assertGreater(result["input_tokens_max"], 1)
        self.assertTrue(result["observations"][0]["target"]["exact_roundtrip"])


if __name__ == "__main__":
    unittest.main()
