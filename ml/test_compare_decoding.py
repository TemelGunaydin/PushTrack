"""Synthetic tests for model-ranked beam diagnostics; no checkpoint/network access."""
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

import torch

from compare_decoding import beam_predictions, decode_candidate, summarize


class DecodingTests(unittest.TestCase):
    def model_and_tokenizer(self, scores=None):
        model = Mock()
        model.generate.return_value = SimpleNamespace(
            sequences=torch.tensor([[0, 1, 4, 2, 0], [0, 1, 5, 2, 0], [0, 1, 6, 2, 0], [0, 1, 7, 2, 0]]),
            sequences_scores=torch.tensor(scores or [-0.1, -0.2, -0.3, -0.4]))
        tokenizer = Mock(pad_token_id=0, eos_token_id=2)
        tokenizer.decode.side_effect = ["Model first", "Exact reference", "Third candidate", "Fourth candidate"]
        return model, tokenizer

    def examples(self):
        return [{"repo_id": "owner/repo", "commit_id": "a" * 40, "input_ids": [1, 8, 2],
                 "labels": [1, 9, 2], "target": "Exact reference"}]

    def test_model_rank_not_reference_controls_choice(self):
        model, tokenizer = self.model_and_tokenizer()
        result = beam_predictions(model, self.examples(), tokenizer, "cpu")[0]
        self.assertEqual(result["prediction"], "Model first")
        self.assertFalse(result["exact_match"])
        self.assertEqual(result["candidates"][1]["prediction"], "Exact reference")
        self.assertEqual(len(result["candidates"]), 4)

    def test_fixed_beam_policy_never_receives_labels(self):
        model, tokenizer = self.model_and_tokenizer()
        beam_predictions(model, self.examples(), tokenizer, "cpu")
        kwargs = model.generate.call_args.kwargs
        self.assertNotIn("labels", kwargs)
        self.assertEqual(kwargs["num_beams"], 4)
        self.assertEqual(kwargs["num_return_sequences"], 4)
        self.assertEqual(kwargs["length_penalty"], 1.0)
        self.assertEqual(kwargs["max_new_tokens"], 64)
        self.assertFalse(kwargs["do_sample"])
        self.assertFalse(kwargs["early_stopping"])
        model.eval.assert_called_once()

    def test_eos_trimming_does_not_rewrite_text(self):
        tokenizer = Mock(eos_token_id=2)
        tokenizer.decode.return_value = "Keep  spaces"
        result = decode_candidate([0, 1, 4, 2, 0, 0], -1.0, tokenizer)
        self.assertEqual(result["generated_ids"], [0, 1, 4, 2])
        self.assertEqual(result["prediction"], "Keep  spaces")
        self.assertTrue(result["eos_emitted"])

    def test_nonfinite_score_rejected(self):
        with self.assertRaisesRegex(ValueError, "Non-finite"):
            decode_candidate([0, 2], float("nan"), Mock())

    def test_unexpected_shape_rejected(self):
        model, tokenizer = self.model_and_tokenizer()
        model.generate.return_value.sequences = torch.tensor([[0, 1, 4, 2, 0]])
        with self.assertRaisesRegex(ValueError, "shape"):
            beam_predictions(model, self.examples(), tokenizer, "cpu")

    def test_reversed_ranks_not_silently_sorted_by_target(self):
        model, tokenizer = self.model_and_tokenizer([-0.2, -0.1, -0.3, -0.4])
        with self.assertRaisesRegex(ValueError, "model-ranked"):
            beam_predictions(model, self.examples(), tokenizer, "cpu")

    def test_metrics_use_top_one_only(self):
        model, tokenizer = self.model_and_tokenizer()
        metrics = summarize(beam_predictions(model, self.examples(), tokenizer, "cpu"))
        self.assertEqual(metrics["examples"], 1)
        self.assertEqual(metrics["exact_matches"], 0)
        self.assertEqual(metrics["eos_emitted"], 1)
        self.assertEqual(metrics["single_line_at_most_72_chars"], 1)


if __name__ == "__main__":
    unittest.main()
