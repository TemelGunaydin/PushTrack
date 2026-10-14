"""Offline tests for the deliberately small training path; no checkpoint download."""
from collections import Counter
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import torch

from train_pilot import (
    PREFIX, WEIGHT_SHA256, batch, encode_row, load_examples, load_initial_model, training_order,
)


class TrainingPilotTests(unittest.TestCase):
    def test_fixed_order_covers_training_examples_only(self):
        order = training_order(11)
        self.assertEqual(len(order), 100)
        self.assertEqual(order, training_order(11))
        self.assertEqual(set(order), set(range(11)))
        self.assertEqual(sorted(Counter(order).values()), [9] * 10 + [10])

    def test_step_budget_is_bounded(self):
        for steps in (0, -1, 101):
            with self.assertRaises(ValueError):
                training_order(11, steps)
        with self.assertRaises(ValueError):
            training_order(0)

    def test_only_diff_enters_encoder(self):
        adapter = Mock()
        adapter.encode.return_value = SimpleNamespace(ids=[1, 7, 2])
        row = {"repo_id": "owner/repository", "commit_id": "a" * 40,
               "diff": "-old\n+new\n", "message": "Replace the old value", "annotation": "never in input"}
        example = encode_row(row, adapter)
        self.assertEqual(adapter.encode.call_args_list[0].args, (PREFIX + row["diff"],))
        self.assertEqual(adapter.encode.call_args_list[1].args, (row["message"],))
        self.assertEqual(example["input_ids"], [1, 7, 2])

    def test_oversized_sequences_are_not_truncated(self):
        row = {"repo_id": "o/r", "commit_id": "a" * 40, "diff": "x", "message": "y"}
        for lengths in ((513, 5), (10, 65)):
            adapter = Mock()
            adapter.encode.side_effect = [SimpleNamespace(ids=[1] * n) for n in lengths]
            with self.assertRaisesRegex(ValueError, "no truncation"):
                encode_row(row, adapter)

    def test_single_example_batch_has_no_padding_targets(self):
        result = batch({"input_ids": [1, 8, 9, 2], "labels": [1, 6, 2]}, "cpu")
        self.assertEqual(result["labels"].tolist(), [[1, 6, 2]])
        self.assertEqual(result["attention_mask"].tolist(), [[1, 1, 1, 1]])
        self.assertEqual(result["input_ids"].dtype, torch.long)

    def test_changed_learning_set_fails_before_encoding(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "train.jsonl").write_text('{}\n')
            adapter = Mock()
            with self.assertRaisesRegex(ValueError, "integrity"):
                load_examples(path, adapter)
            adapter.encode.assert_not_called()

    def test_wrong_weight_hash_never_deserializes(self):
        with tempfile.TemporaryDirectory() as directory, patch("torch.load") as load:
            path = Path(directory)
            (path / "pytorch_model.bin").write_bytes(b"not the approved checkpoint")
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                load_initial_model(path)
            load.assert_not_called()

    def test_safe_loading_and_strict_state_dictionary(self):
        from transformers import T5Config

        config = T5Config(vocab_size=16, d_model=8, d_ff=16, d_kv=4, num_heads=2, num_layers=1)
        state = {"weight": torch.zeros(2)}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "pytorch_model.bin").write_bytes(b"unit fixture only")
            with patch("train_pilot.hashlib.file_digest", return_value=SimpleNamespace(hexdigest=lambda: WEIGHT_SHA256)), \
                 patch("torch.load", return_value=state) as load, \
                 patch("transformers.models.t5.configuration_t5.T5Config.from_pretrained", return_value=config), \
                 patch("transformers.models.t5.modeling_t5.T5ForConditionalGeneration.load_state_dict") as load_state:
                model = load_initial_model(path)
                self.assertEqual(load.call_args.kwargs, {"map_location": "cpu", "weights_only": True})
                load_state.assert_called_once_with(state, strict=True)
                self.assertEqual(model.config.vocab_size, 16)


if __name__ == "__main__":
    unittest.main()
