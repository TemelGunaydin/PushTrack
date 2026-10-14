"""Focused offline training tests; synthetic data and CPU tensors only."""
from collections import Counter
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import torch

from prepare_pilot import digest
from train_corpus import (
    LEARNING_RATE, epoch_batches, evaluate_loss, generate, learning_rate,
    lexical_f1, load_corpus, padded_batch, select_checkpoint, train_epoch, training_plan,
)


def fixture(split, commit, repo):
    text = f"-before {commit}\n+after {commit}\n"
    return {"repo_id": repo, "commit_id": commit, "split": split, "diff": text,
            "diff_sha256": digest(text.encode()), "patch_id": commit,
            "message": "Replace the old value", "training_approved": False,
            "review_status": "quality_screened_with_sample_holds_pending", "input_tokens": 3, "target_tokens": 3}


class CorpusTrainingTests(unittest.TestCase):
    def load_fixture(self, train=None, validation=None):
        rows = {"train": train or [fixture("train", "a" * 40, "one/repo")],
                "validation": validation or [fixture("validation", "b" * 40, "two/repo")]}
        with tempfile.TemporaryDirectory() as temp:
            path, data = Path(temp), {}
            for split, examples in rows.items():
                raw = ("\n".join(json.dumps(row) for row in examples) + "\n").encode()
                (path / (split + ".jsonl")).write_bytes(raw)
                data[split] = (len(examples), digest(raw))
            adapter = Mock()
            adapter.encode.return_value = SimpleNamespace(ids=[1, 7, 2])
            with patch("train_corpus.DATA", data):
                return load_corpus(path, adapter)

    def test_complete_epoch_no_drop_no_repeat(self):
        batches = epoch_batches(9758)
        self.assertEqual(len(batches), 1220)
        self.assertEqual(len(batches[-1]), 6)
        self.assertEqual(Counter(index for batch in batches for index in batch), Counter(range(9758)))
        self.assertEqual(batches, epoch_batches(9758))
        self.assertNotEqual(batches, epoch_batches(9758, seed=43))

    def test_scheduler_keeps_last_batch_learning(self):
        rates = [learning_rate(i, 1220, 61) for i in range(1220)]
        self.assertTrue(all(0 < rate <= LEARNING_RATE for rate in rates))
        self.assertAlmostEqual(rates[60], LEARNING_RATE)
        self.assertLess(rates[0], rates[60])
        self.assertLess(rates[-1], rates[61])
        with self.assertRaises(ValueError):
            learning_rate(1220, 1220, 61)

    def test_three_epoch_plan_preserves_first_epoch_and_covers_every_row(self):
        plan = training_plan(9758, 3)
        self.assertEqual(training_plan(9758, 1), [epoch_batches(9758)])
        self.assertEqual(sum(map(len, plan)), 3660)
        for epoch, batches in enumerate(plan):
            self.assertEqual(batches, epoch_batches(9758, seed=42 + epoch))
            self.assertEqual(len(batches[-1]), 6)
            self.assertEqual(Counter(i for batch in batches for i in batch), Counter(range(9758)))
        self.assertNotEqual(plan[0], plan[1])
        self.assertNotEqual(plan[1], plan[2])

    def test_six_epoch_plan_uses_every_example_six_times(self):
        plan = training_plan(9758, 6)
        self.assertEqual(sum(map(len, plan)), 7320)
        self.assertEqual(Counter(i for batches in plan for batch in batches for i in batch),
                         Counter({i: 6 for i in range(9758)}))
        for epoch, batches in enumerate(plan):
            self.assertEqual(batches, epoch_batches(9758, seed=42 + epoch))
            self.assertEqual(len(batches[-1]), 6)

    def test_six_epoch_schedule_and_validation_selection(self):
        rates = [learning_rate(step, 7320, 366) for step in range(7320)]
        self.assertAlmostEqual(rates[365], LEARNING_RATE)
        self.assertTrue(all(0 < rate <= LEARNING_RATE for rate in rates))
        self.assertLess(rates[1220], rates[1219])
        results = [{"epoch": i + 1, "loss": {"validation": loss, "train": 6 - i}}
                   for i, loss in enumerate([4.0, 3.3, 3.1, 3.0, 3.0, 3.2])]
        self.assertEqual(select_checkpoint(results)["epoch"], 6)
        self.assertEqual(select_checkpoint(results, use_validation=True)["epoch"], 4)

    def test_checkpoint_selection_rejects_invalid_measurements(self):
        for results in ([], [{"epoch": 2, "loss": {"validation": 1.0}}],
                        [{"epoch": 1, "loss": {"validation": float("nan")}}]):
            with self.assertRaises(ValueError):
                select_checkpoint(results, use_validation=True)

    def test_unsupported_epoch_counts_fail(self):
        for epochs in (0, 2, 4, -1, True, 3.0):
            with self.assertRaises(ValueError):
                training_plan(9758, epochs)

    def test_three_epoch_scheduler_uses_global_step(self):
        rates = [learning_rate(step, 3660, 183) for step in range(3660)]
        self.assertAlmostEqual(rates[182], LEARNING_RATE)
        self.assertTrue(all(0 < rate <= LEARNING_RATE for rate in rates))
        self.assertLess(rates[1220], rates[1219])
        self.assertLess(rates[2440], rates[2439])

    def test_training_mode_restored_after_each_evaluation_boundary(self):
        class TinyModel(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.weight = torch.nn.Parameter(torch.tensor(1.0))

            def forward(self, **kwargs):
                if not self.training or not torch.is_grad_enabled():
                    raise AssertionError("Training mode/gradients not restored")
                return SimpleNamespace(loss=self.weight.square())

        model = TinyModel()
        optimizer = torch.optim.SGD(model.parameters(), lr=LEARNING_RATE)
        examples = [{"commit_id": str(i), "input_ids": [1, 2], "labels": [1, 2]} for i in range(3)]
        report = {"steps_completed": 0, "examples_seen": 0, "training_seconds": 0.0}
        log = io.StringIO()
        with tempfile.TemporaryDirectory() as temp:
            for epoch in range(1, 4):
                model.eval()  # The real measurement helpers leave the model in this mode.
                exposures, seconds = train_epoch(model, optimizer, examples,
                    epoch_batches(3, size=2, seed=41 + epoch), 0, "cpu", epoch, 6, 1, report, log, Path(temp))
                self.assertEqual(exposures, Counter({"0": 1, "1": 1, "2": 1}))
                self.assertTrue(model.training)
                report["training_seconds"] += seconds
        records = [json.loads(line) for line in log.getvalue().splitlines()]
        self.assertEqual(report["steps_completed"], 6)
        self.assertEqual(report["examples_seen"], 9)
        self.assertEqual([row["epoch"] for row in records], [1, 1, 2, 2, 3, 3])
        self.assertTrue(all(row["training_mode"] for row in records))
        self.assertLess(float(model.weight.detach()), 1.0)

    def test_nonfinite_loss_stops_before_update(self):
        model = Mock(return_value=SimpleNamespace(loss=torch.tensor(float("nan"), requires_grad=True)))
        optimizer = Mock(param_groups=[{}])
        report = {"steps_completed": 0, "examples_seen": 0, "training_seconds": 0.0}
        with tempfile.TemporaryDirectory() as temp, self.assertRaisesRegex(RuntimeError, "Non-finite training loss"):
            train_epoch(model, optimizer, [{"commit_id": "x", "input_ids": [1, 2], "labels": [1, 2]}],
                        [[0]], 0, "cpu", 1, 1, 0, report, io.StringIO(), Path(temp))
        optimizer.step.assert_not_called()
        self.assertEqual(report["steps_completed"], 0)

    def test_nonfinite_gradient_stops_before_update(self):
        weight = torch.nn.Parameter(torch.tensor(0.0))
        model = Mock(return_value=SimpleNamespace(loss=weight.sqrt()))
        model.parameters.return_value = [weight]
        optimizer = Mock(param_groups=[{}])
        report = {"steps_completed": 0, "examples_seen": 0, "training_seconds": 0.0}
        with tempfile.TemporaryDirectory() as temp, self.assertRaises(RuntimeError):
            train_epoch(model, optimizer, [{"commit_id": "x", "input_ids": [1, 2], "labels": [1, 2]}],
                        [[0]], 0, "cpu", 1, 1, 0, report, io.StringIO(), Path(temp))
        optimizer.step.assert_not_called()
        self.assertEqual(report["steps_completed"], 0)

    def test_padding_masks_inputs_and_ignores_target_padding(self):
        rows = [{"input_ids": [1, 8, 2], "labels": [1, 9, 2]}, {"input_ids": [1, 2], "labels": [1, 2]}]
        batch = padded_batch(rows, 0, "cpu")
        self.assertEqual(batch["input_ids"].tolist(), [[1, 8, 2], [1, 2, 0]])
        self.assertEqual(batch["attention_mask"].tolist(), [[1, 1, 1], [1, 1, 0]])
        self.assertEqual(batch["labels"].tolist(), [[1, 9, 2], [1, 2, -100]])
        self.assertEqual(batch["labels"].dtype, torch.long)

    def test_research_pending_rows_are_explicitly_supported(self):
        examples = self.load_fixture()
        self.assertEqual(len(examples["train"]), 1)
        self.assertEqual(examples["train"][0]["target"], "Replace the old value")

    def test_casefold_repository_overlap_rejected(self):
        with self.assertRaisesRegex(ValueError, "repository-name overlap"):
            self.load_fixture(validation=[fixture("validation", "b" * 40, "ONE/REPO")])

    def test_cross_split_commit_duplicates_rejected(self):
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            self.load_fixture(validation=[fixture("validation", "a" * 40, "two/repo")])

    def test_token_drift_rejected(self):
        row = fixture("train", "a" * 40, "one/repo")
        row["input_tokens"] = 4
        with self.assertRaisesRegex(ValueError, "token lengths differ"):
            self.load_fixture(train=[row])

    def test_wrong_data_hash_rejected_before_encoding(self):
        with tempfile.TemporaryDirectory() as temp:
            path, adapter = Path(temp), Mock()
            (path / "train.jsonl").write_bytes(b"{}\n")
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                load_corpus(path, adapter)
            adapter.encode.assert_not_called()

    def test_changed_approval_flags_are_not_silently_accepted(self):
        row = fixture("train", "a" * 40, "one/repo")
        row["training_approved"] = True
        with self.assertRaisesRegex(ValueError, "Unexpected frozen"):
            self.load_fixture(train=[row])

    def test_loss_is_weighted_by_active_tokens_not_batches(self):
        rows = [{"input_ids": [1, 2], "labels": [1, 2]} for _ in range(8)]
        rows.append({"input_ids": [1, 2], "labels": [1, 3, 4, 2]})
        model = Mock(side_effect=[SimpleNamespace(loss=torch.tensor(2.0)), SimpleNamespace(loss=torch.tensor(6.0))])
        result = evaluate_loss(model, rows, 0, "cpu")
        self.assertEqual(result["examples"], 9)
        self.assertEqual(result["target_tokens"], 20)
        self.assertAlmostEqual(result["token_weighted_loss"], 2.8)
        model.eval.assert_called_once()

    def test_generation_never_receives_target_and_trims_post_eos_padding(self):
        model, tokenizer = Mock(), Mock(pad_token_id=0, eos_token_id=2)
        model.generate.return_value = torch.tensor([[0, 1, 7, 2, 0]])
        tokenizer.decode.return_value = "Fix parsing"
        rows = [{"repo_id": "one/repo", "commit_id": "a" * 40, "target": "Fix parsing", "input_ids": [1, 8, 2], "labels": [1, 7, 2]}]
        result = generate(model, rows, tokenizer, "cpu")
        self.assertNotIn("labels", model.generate.call_args.kwargs)
        self.assertEqual(result["predictions"][0]["generated_ids"], [0, 1, 7, 2])
        self.assertEqual(result["exact_matches"], 1)

    def test_lexical_score_is_only_token_overlap(self):
        self.assertEqual(lexical_f1("Fix parsing", "Fix parsing"), 1)
        self.assertEqual(lexical_f1("Add tests", "Remove code"), 0)
        self.assertAlmostEqual(lexical_f1("Fix parsing", "Fix rendering"), 0.5)


if __name__ == "__main__":
    unittest.main()
