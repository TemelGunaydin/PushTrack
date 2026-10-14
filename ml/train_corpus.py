"""Pinned Chronicle recipes and separately authorized three-/100-epoch CommitBench runs."""

import argparse
from collections import Counter
import datetime as dt
import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
import random
import re
import shutil
import time

from continue_pilot import OfficialTokenizer
from prepare_pilot import PREFIX, digest, json_write
from train_pilot import MODEL, WEIGHT_BYTES, WEIGHT_SHA256, encode_row, file_sha256, load_initial_model

DATA = {
    "train": (9758, "5dd4d286b73bea89456bdb2cb3c5cb23a3757ad38a6baaa37099fe5f0a4d4269"),
    "validation": (962, "76b9d83b60741738c29dc53f8629ec4c0e08434427595a5191682f19f42ba2ee"),
}
COMMITBENCH_DATA = {
    "train": (10000, "2840e70b84b9d8d3e26559724b83076e5c55e75701cdd9148cb1a9f103b151b2"),
    "validation": DATA["validation"],
}
COMMITBENCH_EVIDENCE = {
    "manifest.json": "613b468481b01e2044390e37dce89a93aa5ae86f1c45ebe168fbef517750f295",
    "verification.json": "c56e8a217932e67474cc5a7dffc39883bdf3eda71b6340f90ac08a9ec38cc6e7",
    "quality-review.json": "6fea3e218762220b414d7e84eaf413a364b4d8211a6d401a8fc9c3998e0e99e1",
    "quality-review-verification.json": "8db07127a9d96ccea1231e3e6fc0f4097f8830d9205f2e6f0eb83a2241723059",
}
DATA_VERSIONS = ("chronicle-frozen", "commitbench-source-0002")
SEED = 42
EPOCHS = 1
BATCH_SIZE = 8
LEARNING_RATE = 5e-5
TRAIN_GENERATION_SAMPLE = 64


def save_report(output, report):
    temporary = output / "report.tmp"
    json_write(temporary, report)
    temporary.replace(output / "report.json")


def load_corpus(directory, adapter):
    """Only this frozen pending set is authorized for this research experiment.

    Approval to execute this run is not certification of every original label
    or of exhaustive fork-family separation. Original artifact flags stay intact.
    """
    examples, identities, patches = {}, set(), set()
    for split, (count, sha) in DATA.items():
        examples[split] = load_split(directory / (split + ".jsonl"), split, count, sha,
            "quality_screened_with_sample_holds_pending", adapter, identities, patches)
    check_repository_separation(examples)
    return examples


def load_split(path, split, count, sha, review_status, adapter, identities, patches, commitbench=False):
    raw = path.read_bytes()
    if digest(raw) != sha:
        raise ValueError(f"Frozen research-data hash mismatch: {split}")
    rows = [json.loads(line) for line in raw.splitlines()]
    if len(rows) != count:
        raise ValueError("Frozen research-data count mismatch")
    examples = []
    for row in rows:
        if (row["split"] != split or row["training_approved"] is not False
                or row["review_status"] != review_status
                or digest(row["diff"].encode()) != row["diff_sha256"]):
            raise ValueError("Unexpected frozen research-data record")
        if commitbench:
            dataset = row["dataset"]
            if (dataset["name"] != "Maxscha/commitbench"
                    or dataset["revision"] != "1500792cd6998308da046ba72b688156b2ffa471"
                    or dataset["license"] != "CC-BY-NC-4.0" or dataset["shard"] != "train.csv"
                    or dataset["shard_sha256"] != "23adc5ca32088e9991882ccd252b0579b95d22d07dc9b0bce739f4e920c96f04"
                    or row["source"]["license"] != "MIT"
                    or row["integrity_status"] != "complete_original_diff_applies_to_exact_snapshots"
                    or row["usage_status"] != "noncommercial_research_only_pending_quality_and_distribution_clearance"):
                raise ValueError("Unexpected CommitBench provenance/integrity/license flags")
        if row["commit_id"] in identities or row["patch_id"] in patches:
            raise ValueError("Duplicate commit or stable patch in research data")
        identities.add(row["commit_id"])
        patches.add(row["patch_id"])
        example = encode_row(row, adapter)
        if (len(example["input_ids"]), len(example["labels"])) != (row["input_tokens"], row["target_tokens"]):
            raise ValueError("Recorded token lengths differ; no truncation allowed")
        examples.append(example)
    return examples


def check_repository_separation(examples):
    if {r["repo_id"].casefold() for r in examples["train"]} & {r["repo_id"].casefold() for r in examples["validation"]}:
        raise ValueError("Training/validation repository-name overlap")


def load_commitbench(workspace, adapter):
    root = workspace / "data" / "commitbench-0001" / "sources-0002"
    evidence = {}
    for name, expected in COMMITBENCH_EVIDENCE.items():
        raw = (root / name).read_bytes()
        if digest(raw) != expected:
            raise ValueError(f"Pinned CommitBench evidence mismatch: {name}")
        evidence[name] = json.loads(raw)
    manifest, proof = evidence["manifest.json"], evidence["verification.json"]
    if (manifest["version"] != "commitbench-source-expansion-0001-pending"
            or manifest["license"] != "CC-BY-NC-4.0" or manifest["training_approved"] is not False
            or manifest["research_run_authorized"] is not False or manifest["target_changes"] != 0
            or (manifest["train"]["rows"], manifest["train"]["sha256"]) != COMMITBENCH_DATA["train"]
            or proof["status"] != "passed" or proof["optimizer_updates"] != 0
            or evidence["quality-review-verification.json"]["status"] != "passed"
            or evidence["quality-review.json"]["dataset_targets_changed"] != 0
            or evidence["quality-review.json"]["training_approved"] is not False):
        raise ValueError("Unexpected CommitBench pending-version evidence")
    identities, patches = set(), set()
    count, sha = COMMITBENCH_DATA["train"]
    train = load_split(root / "train-pending.jsonl", "train", count, sha,
        "source_checked_pending_quality_review", adapter, identities, patches, commitbench=True)
    count, sha = COMMITBENCH_DATA["validation"]
    validation = load_split(workspace / "data" / "corpus-0001" / "audit-0002" / "post-review-pending" / "validation.jsonl",
        "validation", count, sha, "quality_screened_with_sample_holds_pending", adapter, identities, patches)
    examples = {"train": train, "validation": validation}
    check_repository_separation(examples)
    return examples


def data_spec(data_version):
    if data_version not in DATA_VERSIONS:
        raise ValueError("Only explicitly pinned research-data versions are supported")
    return COMMITBENCH_DATA if data_version == "commitbench-source-0002" else DATA


def epoch_batches(count, size=BATCH_SIZE, seed=SEED):
    if count < 1 or size < 1:
        raise ValueError("Positive example and batch counts required")
    order = list(range(count))
    random.Random(seed).shuffle(order)
    return [order[offset:offset + size] for offset in range(0, count, size)]


def training_plan(count, epochs):
    if type(epochs) is not int or epochs not in (1, 3, 6, 100):
        raise ValueError("Only fixed one-, three-, six-, or 100-epoch plans are supported")
    return [epoch_batches(count, seed=SEED + index) for index in range(epochs)]


def select_checkpoint(results, use_validation=False):
    if not results or [row["epoch"] for row in results] != list(range(1, len(results) + 1)):
        raise ValueError("Expected complete ordered epoch results")
    if any(not math.isfinite(row["loss"]["validation"]) for row in results):
        raise ValueError("Cannot select from non-finite validation losses")
    # Only the separately declared six-epoch recipe uses validation selection.
    # Equal losses choose the earlier epoch; semantic sample judgments are not used.
    return min(results, key=lambda row: (row["loss"]["validation"], row["epoch"])) if use_validation else results[-1]


def learning_rate(step_index, total, warmup):
    if not 0 <= step_index < total or not 0 <= warmup < total:
        raise ValueError("Invalid scheduler position")
    if step_index < warmup:
        return LEARNING_RATE * (step_index + 1) / warmup
    # Last actual update remains positive; zero is reached after the full run.
    return LEARNING_RATE * (total - step_index) / (total - warmup + 1)


def padded_batch(examples, pad_id, device):
    import torch

    if not examples:
        raise ValueError("Cannot construct an empty batch")
    input_length = max(len(row["input_ids"]) for row in examples)
    target_length = max(len(row["labels"]) for row in examples)
    inputs, masks, labels = [], [], []
    for row in examples:
        missing = input_length - len(row["input_ids"])
        inputs.append(row["input_ids"] + [pad_id] * missing)
        masks.append([1] * len(row["input_ids"]) + [0] * missing)
        labels.append(row["labels"] + [-100] * (target_length - len(row["labels"])))
    return {name: torch.tensor(values, dtype=torch.long, device=device)
            for name, values in (("input_ids", inputs), ("attention_mask", masks), ("labels", labels))}


def evaluate_loss(model, examples, pad_id, device):
    import torch

    model.eval()
    weighted_loss, tokens, batches = 0.0, 0, []
    with torch.inference_mode():
        for offset in range(0, len(examples), BATCH_SIZE):
            rows = examples[offset:offset + BATCH_SIZE]
            value = float(model(**padded_batch(rows, pad_id, device), use_cache=False).loss)
            if not math.isfinite(value):
                raise RuntimeError("Non-finite evaluation loss")
            active = sum(len(row["labels"]) for row in rows)
            weighted_loss += value * active
            tokens += active
            batches.append({"offset": offset, "examples": len(rows), "target_tokens": active, "loss": value})
    return {"examples": len(examples), "target_tokens": tokens, "token_weighted_loss": weighted_loss / tokens,
            "batches": batches}


def lexical_f1(prediction, target):
    # A cheap lexical diagnostic, not a semantic-faithfulness metric.
    predicted = Counter(re.findall(r"\w+|[^\w\s]", prediction.casefold()))
    expected = Counter(re.findall(r"\w+|[^\w\s]", target.casefold()))
    total = sum(predicted.values()) + sum(expected.values())
    return 2 * sum((predicted & expected).values()) / total if total else 1.0


def generate(model, examples, tokenizer, device):
    import torch

    model.eval()
    predictions = []
    with torch.inference_mode():
        for offset in range(0, len(examples), BATCH_SIZE):
            rows = examples[offset:offset + BATCH_SIZE]
            tensors = padded_batch(rows, tokenizer.pad_token_id, device)
            sequences = model.generate(input_ids=tensors["input_ids"], attention_mask=tensors["attention_mask"],
                                       do_sample=False, num_beams=1, max_new_tokens=64, use_cache=True).tolist()
            for row, ids in zip(rows, sequences):
                ended = tokenizer.eos_token_id in ids[1:]
                if ended:
                    ids = ids[:ids.index(tokenizer.eos_token_id, 1) + 1]
                prediction = tokenizer.decode(ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)
                predictions.append({"repo_id": row["repo_id"], "commit_id": row["commit_id"], "target": row["target"],
                                    "prediction": prediction, "generated_ids": ids, "eos_emitted": ended,
                                    "exact_match": prediction == row["target"],
                                    "lexical_f1": lexical_f1(prediction, row["target"])})
            if offset == 0 or (offset // BATCH_SIZE + 1) % 25 == 0:
                print(f"Generated {len(predictions)}/{len(examples)} subjects", flush=True)
    counts = Counter(row["prediction"] for row in predictions)
    return {"examples": len(examples), "exact_matches": sum(row["exact_match"] for row in predictions),
            "mean_lexical_f1": sum(row["lexical_f1"] for row in predictions) / len(predictions),
            "eos_emitted": sum(row["eos_emitted"] for row in predictions),
            "single_line_at_most_72_chars": sum(bool(row["prediction"].strip()) and len(row["prediction"]) <= 72
                                                and "\n" not in row["prediction"] and "\r" not in row["prediction"] for row in predictions),
            "unique_predictions": len(counts), "most_common_predictions": counts.most_common(5), "predictions": predictions}


def measure(model, examples, tokenizer):
    result = {"loss": {}, "generation": {}}
    for split in ("train", "validation"):
        print(f"Measuring {split} loss on all {len(examples[split])} examples", flush=True)
        result["loss"][split] = evaluate_loss(model, examples[split], tokenizer.pad_token_id, "cuda")
    sample = sorted(examples["train"], key=lambda row: digest(("train-generation-42:" + row["commit_id"]).encode()))[:TRAIN_GENERATION_SAMPLE]
    result["generation"]["train_sample"] = generate(model, sample, tokenizer, "cuda")
    result["generation"]["validation"] = generate(model, examples["validation"], tokenizer, "cuda")
    return result


def train_epoch(model, optimizer, examples, order, pad_id, device, epoch, total, warmup, report, log, output):
    """Training-only updates; restore dropout after every evaluation boundary."""
    import torch

    model.train()
    sync = torch.cuda.synchronize if device == "cuda" else lambda: None
    exposures = Counter()
    sync()
    started = time.perf_counter()
    for epoch_step, indices in enumerate(order, 1):
        step = report["steps_completed"]
        rows = [examples[index] for index in indices]
        rate = learning_rate(step, total, warmup)
        for group in optimizer.param_groups:
            group["lr"] = rate
        optimizer.zero_grad(set_to_none=True)
        loss = model(**padded_batch(rows, pad_id, device), use_cache=False).loss
        value = float(loss.detach())
        if not math.isfinite(value):
            raise RuntimeError("Non-finite training loss; stopped before optimizer update")
        loss.backward()
        norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0, error_if_nonfinite=True)
        optimizer.step()
        exposures.update(row["commit_id"] for row in rows)
        report.update(steps_completed=step + 1, examples_seen=report["examples_seen"] + len(rows))
        log.write(json.dumps({"step": step + 1, "epoch": epoch, "epoch_step": epoch_step,
                              "train_indices": indices, "commit_ids": [row["commit_id"] for row in rows],
                              "learning_rate": rate, "loss_with_dropout": value,
                              "gradient_norm_before_clip": float(norm), "training_mode": model.training}) + "\n")
        log.flush()
        if epoch_step == 1 or (step + 1) % 50 == 0 or epoch_step == len(order):
            sync()
            elapsed = time.perf_counter() - started
            report["training_elapsed_seconds"] = report["training_seconds"] + elapsed
            save_report(output, report)
            print(f'Epoch {epoch}: step {step+1}/{total}; total exposures {report["examples_seen"]}; loss {value:.4f}; training {report["training_elapsed_seconds"]:.1f}s', flush=True)
    sync()
    seconds = time.perf_counter() - started
    if len(exposures) != len(examples) or set(exposures.values()) != {1}:
        raise RuntimeError("Expected exactly one exposure per training example in each epoch")
    return exposures, seconds


def check_disk_reserve(output, epochs):
    # A hundred full checkpoints need about 24.2 GB; never prune old evidence.
    # Keep a 20 GB reserve plus the next checkpoint and evaluation/log overhead.
    if epochs == 100 and shutil.disk_usage(output).free < 20_000_000_000 + WEIGHT_BYTES + 1_000_000_000:
        raise RuntimeError("Insufficient disk reserve; preserve artifacts, do not restart automatically")


def run(workspace, output, epochs=EPOCHS, data_version="chronicle-frozen"):
    if platform.system() != "Windows":
        raise RuntimeError("Train natively on Windows")
    spec = data_spec(data_version)
    commitbench = data_version == "commitbench-source-0002"
    if commitbench and (type(epochs) is not int or epochs not in (3, 100)):
        raise ValueError("CommitBench supports only fixed three- or 100-epoch recipes; each needs user authorization")
    if not commitbench and (type(epochs) is not int or epochs not in (1, 3, 6)):
        raise ValueError("Chronicle supports only its preserved one-, three-, or six-epoch recipes")
    orders = training_plan(spec["train"][0], epochs)
    if output.exists():
        raise ValueError("Output exists; preserve the previous run")
    for name in ("TEMP", "TMP"):
        os.environ[name] = str(workspace / ".tmp")
    os.environ.update(HF_HUB_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1", CUBLAS_WORKSPACE_CONFIG=":4096:8",
                      HF_HOME=str(workspace / ".cache" / "huggingface"))
    import torch

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA unavailable; no CPU fallback")
    torch.manual_seed(SEED)
    random.seed(SEED)
    torch.use_deterministic_algorithms(True)
    torch.set_float32_matmul_precision("highest")
    torch.backends.cudnn.benchmark = False
    torch.set_num_threads(4)
    directory = workspace / "checkpoints" / "codet5-small"
    weights = directory / "pytorch_model.bin"
    if not weights.is_file() or weights.stat().st_size != WEIGHT_BYTES:
        raise ValueError("Existing original checkpoint required; downloads are not allowed")
    output.mkdir(parents=True)
    (output / "provenance").mkdir()
    for name in ("train_corpus.py", "test_train_corpus.py", "test_train_commitbench.py", "train_pilot.py", "continue_pilot.py", "compare_tokenizers.py", "prepare_pilot.py", "requirements-train.in", "requirements-train.lock"):
        shutil.copyfile(Path(__file__).parent / name, output / "provenance" / name)
    report = {"status": "running", "stage": "loading", "started_at_utc": dt.datetime.now(dt.UTC).isoformat(),
              "epochs": epochs, "epochs_completed": 0, "epoch_shuffle_seeds": list(range(SEED, SEED + epochs)),
              "batch_size": BATCH_SIZE, "seed": SEED, "maximum_learning_rate": LEARNING_RATE,
              "optimizer": "AdamW", "weight_decay": 0.01, "betas": [0.9, 0.999], "epsilon": 1e-8,
              "scheduler": "linear warmup/decay", "gradient_clip_norm": 1.0, "precision": "float32", "attention": "eager",
              "input_prefix": PREFIX, "input_limit": 512, "target_limit": 64, "padding_label_id": -100,
              "model_repo": MODEL["repo"], "model_revision": MODEL["revision"], "initial_weights_sha256": WEIGHT_SHA256,
              "data_version": data_version,
              "data": {split: {"examples": count, "sha256": sha} for split, (count, sha) in spec.items()},
              "data_license": "CC-BY-NC-4.0" if commitbench else "Original source MIT policy; clearance limitations remain",
              "pinned_data_evidence": COMMITBENCH_EVIDENCE if commitbench else {},
              "authorization": (f"User explicitly authorized one {epochs}-epoch noncommercial research run on all 10000 original CommitBench targets; 9960 unreviewed labels and family/privacy/pretraining/distribution limits disclosed; no proposal application"
                                if commitbench else "User explicitly authorized full-dataset research training after disclosure of remaining quality/fork limitations"),
              "data_quality_certified": False, "validation_used_for_updates": False,
              "checkpoint_selection": ("Lowest full validation loss among six epochs; earliest epoch wins ties; no early stopping or extension"
                                       if epochs == 6 else "Final predeclared epoch; no validation-based early stopping or automatic extension"),
              "comparison_note": ("The 100-epoch recipe starts from original weights and scales global warmup/decay to 125000 updates, unlike the 3750-update three-epoch recipe; not an isolated extra-epoch effect"
                                  if epochs == 100 else "CommitBench uses 10000 instead of 9758 rows, changing update count and warmup/decay; this is not an isolated source-quality effect"
                                  if commitbench else "The longer recipe also scales warmup/decay over its full update budget; this is not an isolated epoch-count effect"),
              "minimum_disk_reserve_bytes": 20_000_000_000 if epochs == 100 else None,
              "epoch_results": [], "training_seconds": 0.0,
              "limitations": ["Most original labels remain unreviewed weak supervision", "Canonical/fork metadata is incomplete", "Metrics are exploratory, not proven generalization or deployment readiness"],
              "generation": {"do_sample": False, "num_beams": 1, "max_new_tokens": 64, "train_sample_size": TRAIN_GENERATION_SAMPLE, "validation": "all"},
              "torch": torch.__version__, "transformers": importlib.metadata.version("transformers"),
              "python": platform.python_version(), "cuda_runtime": torch.version.cuda, "device": torch.cuda.get_device_name(0),
              "source_sha256": digest(Path(__file__).read_bytes()), "steps_completed": 0, "examples_seen": 0}
    save_report(output, report)
    try:
        adapter = OfficialTokenizer(directory)
        corpus = workspace / "data" / "corpus-0001" / "audit-0002" / "post-review-pending"
        examples = load_commitbench(workspace, adapter) if commitbench else load_corpus(corpus, adapter)
        model = load_initial_model(directory).to("cuda")
        report["parameters"] = sum(parameter.numel() for parameter in model.parameters())
        report["trainable_parameters"] = sum(parameter.numel() for parameter in model.parameters() if parameter.requires_grad)
        if report["parameters"] != 60_492_288 or report["parameters"] != report["trainable_parameters"]:
            raise RuntimeError("Expected full-parameter CodeT5-small fine-tuning")
        probe = model.shared.weight[:2].detach().cpu().clone()
        total = sum(len(order) for order in orders)
        warmup = math.ceil(total * 0.05)
        report.update(optimizer_steps_planned=total, warmup_steps=warmup, stage="baseline")
        save_report(output, report)
        torch.cuda.reset_peak_memory_stats()
        baseline = measure(model, examples, adapter.tokenizer)
        json_write(output / "baseline.json", baseline)
        report["baseline_loss"] = {split: value["token_weighted_loss"] for split, value in baseline["loss"].items()}
        optimizer = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=0.01)
        exposures = Counter()
        with (output / "steps.jsonl").open("x", encoding="utf-8", newline="\n") as log:
            for epoch, order in enumerate(orders, 1):
                check_disk_reserve(output, epochs)
                report.update(stage="training", current_epoch=epoch)
                save_report(output, report)
                epoch_exposures, seconds = train_epoch(model, optimizer, examples["train"], order,
                    adapter.tokenizer.pad_token_id, "cuda", epoch, total, warmup, report, log, output)
                exposures.update(epoch_exposures)
                report["training_seconds"] += seconds
                report["epochs_completed"] = epoch
                # Preserve each completed epoch before measuring it. No optimizer state/resume.
                report["stage"] = "saving"
                save_report(output, report)
                check_disk_reserve(output, epochs)
                checkpoint = output / ("checkpoint" if epoch == epochs else f"checkpoint-epoch-{epoch}")
                model.save_pretrained(str(checkpoint), safe_serialization=True)
                adapter.tokenizer.save_pretrained(str(checkpoint))
                tensors = list(checkpoint.glob("*.safetensors"))
                if not tensors or list(checkpoint.glob("*.bin")):
                    raise RuntimeError("Expected safetensors-only saved weights")
                saved = {path.name: {"bytes": path.stat().st_size, "sha256": file_sha256(path)} for path in tensors}
                model.zero_grad(set_to_none=True)
                if epoch == epochs:
                    report["saved_checkpoint"] = saved
                    del optimizer
                report["stage"] = "epoch_evaluation"
                save_report(output, report)
                measured = measure(model, examples, adapter.tokenizer)
                filename = "final.json" if epoch == epochs else f"epoch-{epoch}.json"
                json_write(output / filename, measured)
                report["epoch_results"].append({"epoch": epoch, "steps_completed": report["steps_completed"],
                    "training_seconds": seconds, "checkpoint": checkpoint.name, "saved_checkpoint": saved,
                    "measurement_file": filename, "loss": {split: value["token_weighted_loss"] for split, value in measured["loss"].items()},
                    "generation": {split: {key: value for key, value in metrics.items() if key != "predictions"}
                                   for split, metrics in measured["generation"].items()}})
                save_report(output, report)
                print(f'Epoch {epoch}/{epochs} measured: {report["epoch_results"][-1]["loss"]}', flush=True)
        if len(exposures) != len(examples["train"]) or set(exposures.values()) != {epochs}:
            raise RuntimeError("Expected exactly the declared epoch count for every training example")
        report["exposure_summary"] = {"unique_examples": len(exposures), "minimum": min(exposures.values()), "maximum": max(exposures.values())}
        report["embedding_probe_changed"] = not torch.equal(probe, model.shared.weight[:2].detach().cpu())
        selected = select_checkpoint(report["epoch_results"], use_validation=epochs == 6)
        report.update(selected_epoch=selected["epoch"], selected_checkpoint=selected["checkpoint"],
                      selected_measurement_file=selected["measurement_file"])
        final = measured
        report["final_loss"] = {split: value["token_weighted_loss"] for split, value in final["loss"].items()}
        report["generation_metrics"] = {stage: {split: {key: value for key, value in metrics.items() if key != "predictions"}
                                               for split, metrics in measurements["generation"].items()}
                                        for stage, measurements in (("baseline", baseline), ("final", final))}
        report["peak_cuda_tensor_allocated_bytes"] = torch.cuda.max_memory_allocated()
        report["peak_cuda_tensor_reserved_bytes"] = torch.cuda.max_memory_reserved()
        report.update(status="completed", stage="completed")
    except Exception as error:
        report.update(status="failed", error=f"{type(error).__name__}: {error}")
        raise
    finally:
        report["finished_at_utc"] = dt.datetime.now(dt.UTC).isoformat()
        save_report(output, report)
    print(json.dumps({key: report[key] for key in ("status", "steps_completed", "examples_seen", "training_seconds", "baseline_loss", "final_loss")}, indent=2), flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=Path(r"D:\PushTrackML"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--epochs", type=int, choices=(1, 3, 6, 100), default=EPOCHS,
                        help="Fixed research recipe; each new run requires user authorization")
    parser.add_argument("--data-version", choices=DATA_VERSIONS, default="chronicle-frozen",
                        help="CommitBench permits only separately authorized fixed three- or 100-epoch research runs")
    args = parser.parse_args()
    run(args.workspace, args.output, epochs=args.epochs, data_version=args.data_version)


if __name__ == "__main__":
    main()
