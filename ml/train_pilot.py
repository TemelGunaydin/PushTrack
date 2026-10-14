"""A fixed, 100-step CodeT5-small learning demonstration on native Windows."""

import argparse
from collections import Counter
import datetime as dt
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
import random
import shutil
import time

from compare_tokenizers import CANDIDATES, verify_asset
from continue_pilot import OfficialTokenizer
from prepare_pilot import Network, PREFIX, digest, json_write, pinned_download

MODEL = CANDIDATES["codet5-small"]
WEIGHT_BYTES = 242_026_427
WEIGHT_SHA256 = "968fb0f45e1efc8cf3dd50012d1f82ad82098107cbadde2c0fdd8e61bac02908"
DATA_HASHES = {
    "train": "197ff7e95d76256c3cf5a13854cda995903e91d341c096247b4882444538d095",
    "validation": "d0a84bf9f54c98e4d8be9233aefba2908f3fd2360503587a07b57fa88e54b70c",
}
SEED = 42
STEPS = 100
LEARNING_RATE = 0.0005


def file_sha256(path):
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def prepare_checkpoint(workspace):
    """One allowlisted weight file; reuse already verified local tokenizer assets."""
    source = workspace / "runs" / "tokenizer-0002" / "codet5-small"
    directory = workspace / "checkpoints" / "codet5-small"
    directory.mkdir(parents=True, exist_ok=True)
    for name, (size, blob) in MODEL["files"].items():
        data = (source / name).read_bytes()
        verify_asset(data, size, blob)
        destination = directory / name
        if destination.exists() and destination.read_bytes() != data:
            raise ValueError(f"Existing checkpoint asset differs: {name}")
        if not destination.exists():
            destination.write_bytes(data)
    network = Network(budget=WEIGHT_BYTES)
    path = directory / "pytorch_model.bin"
    url = f'https://huggingface.co/{MODEL["repo"]}/resolve/{MODEL["revision"]}/pytorch_model.bin'
    pinned_download(network, path, url, WEIGHT_BYTES, WEIGHT_SHA256)
    receipt = {"recorded_at_utc": dt.datetime.now(dt.UTC).isoformat(), "repo": MODEL["repo"],
               "revision": MODEL["revision"], "url": url, "bytes": WEIGHT_BYTES,
               "sha256": WEIGHT_SHA256, "response_body_bytes": network.received}
    # Preserve the initial acquisition receipt when the verified file is reused.
    if not (directory / "acquisition.json").exists():
        json_write(directory / "acquisition.json", receipt)
    return directory, receipt


def encode_row(row, adapter):
    # Neither identity, subject, annotations, nor source metadata enter the encoder.
    inputs = adapter.encode(PREFIX + row["diff"]).ids
    labels = adapter.encode(row["message"]).ids
    if not 1 <= len(inputs) <= 512 or not 1 <= len(labels) <= 64:
        raise ValueError("Token budget exceeded; no truncation is allowed")
    return {"repo_id": row["repo_id"], "commit_id": row["commit_id"],
            "input_ids": inputs, "labels": labels, "target": row["message"]}


def load_examples(directory, adapter):
    result = {}
    for split, expected_hash in DATA_HASHES.items():
        data = (directory / (split + ".jsonl")).read_bytes()
        if digest(data) != expected_hash:
            raise ValueError(f"Learning-set integrity failed: {split}")
        rows = [json.loads(line) for line in data.splitlines()]
        expected_count = 11 if split == "train" else 5
        if len(rows) != expected_count or any(
            r["split"] != split or r["review_status"] != "assistant_curated_for_learning"
            or digest(r["diff"].encode()) != r["diff_sha256"] for r in rows
        ):
            raise ValueError(f"Unexpected learning-set records: {split}")
        result[split] = [encode_row(row, adapter) for row in rows]
    train_repos = {r["repo_id"].casefold() for r in result["train"]}
    if train_repos & {r["repo_id"].casefold() for r in result["validation"]}:
        raise ValueError("Training/validation project overlap")
    return result


def training_order(count, steps=STEPS, seed=SEED):
    if count < 1 or not 1 <= steps <= STEPS:
        raise ValueError("Expected examples and 1-100 optimizer steps")
    rng, order = random.Random(seed), []
    while len(order) < steps:
        epoch = list(range(count))
        rng.shuffle(epoch)
        order.extend(epoch)
    return order[:steps]


def batch(example, device):
    import torch

    # Batch size one: sequences are unpadded, so every label token is active.
    inputs = torch.tensor([example["input_ids"]], dtype=torch.long, device=device)
    labels = torch.tensor([example["labels"]], dtype=torch.long, device=device)
    return {"input_ids": inputs, "attention_mask": torch.ones_like(inputs), "labels": labels}


def load_initial_model(directory):
    import torch
    from transformers import T5Config, T5ForConditionalGeneration

    with (directory / "pytorch_model.bin").open("rb") as file:
        if hashlib.file_digest(file, "sha256").hexdigest() != WEIGHT_SHA256:
            raise ValueError("Checkpoint hash mismatch before safe loading")
        file.seek(0)
        state = torch.load(file, map_location="cpu", weights_only=True)
    if not isinstance(state, dict) or not state or not all(
        isinstance(key, str) and isinstance(value, torch.Tensor) for key, value in state.items()
    ):
        raise ValueError("Expected a tensor-only state dictionary")
    config = T5Config.from_pretrained(str(directory), local_files_only=True)
    config._attn_implementation = "eager"
    model = T5ForConditionalGeneration(config)
    model.load_state_dict(state, strict=True)
    model.tie_weights()
    return model


def evaluate(model, examples, tokenizer, device):
    import torch

    model.eval()
    results = []
    with torch.inference_mode():
        for example in examples:
            tensors = batch(example, device)
            loss = float(model(**tensors, use_cache=False).loss)
            if not math.isfinite(loss):
                raise RuntimeError("Non-finite evaluation loss")
            generated = model.generate(
                input_ids=tensors["input_ids"], attention_mask=tensors["attention_mask"],
                do_sample=False, num_beams=1, max_new_tokens=64, use_cache=True,
            )[0].tolist()
            prediction = tokenizer.decode(generated, skip_special_tokens=True, clean_up_tokenization_spaces=False)
            results.append({"repo_id": example["repo_id"], "commit_id": example["commit_id"],
                            "target": example["target"], "prediction": prediction,
                            "generated_ids": generated, "eos_emitted": tokenizer.eos_token_id in generated[1:],
                            "exact_match": prediction == example["target"],
                            "loss": loss, "target_tokens": len(example["labels"])})
    return {"examples": len(results), "exact_matches": sum(r["exact_match"] for r in results),
            "token_weighted_loss": sum(r["loss"] * r["target_tokens"] for r in results)
            / sum(r["target_tokens"] for r in results), "predictions": results}


def run(workspace, output):
    if platform.system() != "Windows":
        raise RuntimeError("This experiment must run natively on Windows")
    if output.exists():
        raise ValueError("Output exists; preserve the previous run")
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
    os.environ["CUBLAS_WORKSPACE_CONFIG"] = ":4096:8"
    import torch

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA unavailable; no CPU training fallback")
    torch.manual_seed(SEED)
    random.seed(SEED)
    torch.use_deterministic_algorithms(True)
    torch.set_float32_matmul_precision("highest")
    torch.backends.cudnn.benchmark = False
    torch.set_num_threads(4)
    output.mkdir(parents=True)
    provenance = output / "provenance"
    provenance.mkdir()
    for name in ("train_pilot.py", "continue_pilot.py", "compare_tokenizers.py", "prepare_pilot.py",
                 "requirements-train.in", "requirements-train.lock"):
        shutil.copyfile(Path(__file__).parent / name, provenance / name)
    report = {"status": "running", "started_at_utc": dt.datetime.now(dt.UTC).isoformat(),
              "model_repo": MODEL["repo"], "model_revision": MODEL["revision"],
              "seed": SEED, "max_steps": STEPS, "steps_completed": 0,
              "batch_size": 1, "learning_rate": LEARNING_RATE, "weight_decay": 0.01,
              "optimizer": "AdamW", "betas": [0.9, 0.999], "epsilon": 1e-8,
              "gradient_clip_norm": 1.0, "scheduler": None, "precision": "float32",
              "attention": "eager", "input_prefix": PREFIX, "input_limit": 512, "target_limit": 64,
              "generation": {"do_sample": False, "num_beams": 1, "max_new_tokens": 64},
              "data_sha256": DATA_HASHES, "python": platform.python_version(),
              "torch": torch.__version__, "cuda_runtime": torch.version.cuda,
              "transformers": importlib.metadata.version("transformers"),
              "device": torch.cuda.get_device_name(0), "validation_used_for_updates": False,
              "source_sha256": digest(Path(__file__).read_bytes()),
              "scope": "Tiny learning demonstration only; not a generalization or deployment benchmark"}
    json_write(output / "report.json", report)
    try:
        directory, acquisition = prepare_checkpoint(workspace)
        report["checkpoint_acquisition"] = acquisition
        adapter = OfficialTokenizer(directory)
        examples = load_examples(workspace / "data" / "pilot-0002" / "learning-set", adapter)
        model = load_initial_model(directory).to("cuda")
        report["parameters"] = sum(p.numel() for p in model.parameters())
        report["trainable_parameters"] = sum(p.numel() for p in model.parameters() if p.requires_grad)
        probe = model.shared.weight[:2].detach().cpu().clone()
        print(f'Loaded {report["parameters"]:,} parameters safely on {report["device"]}', flush=True)
        baseline = {split: evaluate(model, rows, adapter.tokenizer, "cuda") for split, rows in examples.items()}
        json_write(output / "baseline.json", baseline)
        report["baseline_loss"] = {split: value["token_weighted_loss"] for split, value in baseline.items()}
        print("Baseline losses:", report["baseline_loss"], flush=True)
        optimizer = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=0.01)
        model.train()
        exposures = Counter()
        torch.cuda.synchronize()
        started = time.perf_counter()
        with (output / "steps.jsonl").open("x", encoding="utf-8", newline="\n") as log:
            for step, index in enumerate(training_order(len(examples["train"])), 1):
                example = examples["train"][index]
                optimizer.zero_grad(set_to_none=True)
                loss = model(**batch(example, "cuda"), use_cache=False).loss
                value = float(loss.detach())
                if not math.isfinite(value):
                    raise RuntimeError("Non-finite training loss; stopping before update")
                loss.backward()
                norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0, error_if_nonfinite=True)
                optimizer.step()
                exposures[example["commit_id"]] += 1
                report["steps_completed"] = step
                log.write(json.dumps({"step": step, "train_index": index, "commit_id": example["commit_id"],
                                      "loss_with_dropout": value, "gradient_norm_before_clip": float(norm)}) + "\n")
                log.flush()
                if step == 1 or step % 10 == 0:
                    print(f"Step {step}/{STEPS}: training loss {value:.6f}", flush=True)
        torch.cuda.synchronize()
        report["training_seconds"] = time.perf_counter() - started
        report["train_exposures"] = dict(exposures)
        report["embedding_probe_changed"] = not torch.equal(probe, model.shared.weight[:2].detach().cpu())
        final = {split: evaluate(model, rows, adapter.tokenizer, "cuda") for split, rows in examples.items()}
        json_write(output / "final.json", final)
        report["final_loss"] = {split: value["token_weighted_loss"] for split, value in final.items()}
        report["exact_matches"] = {split: {"baseline": baseline[split]["exact_matches"], "final": final[split]["exact_matches"]}
                                   for split in examples}
        checkpoint = output / "checkpoint"
        model.save_pretrained(str(checkpoint), safe_serialization=True)
        adapter.tokenizer.save_pretrained(str(checkpoint))
        tensors = list(checkpoint.glob("*.safetensors"))
        if not tensors or list(checkpoint.glob("*.bin")):
            raise RuntimeError("Expected a safetensors-only output checkpoint")
        report["saved_checkpoint"] = {path.name: {"bytes": path.stat().st_size,
            "sha256": file_sha256(path)} for path in tensors}
        report["status"] = "completed"
        print("Final losses:", report["final_loss"], flush=True)
        print("Exact reference matches:", report["exact_matches"], flush=True)
    except Exception as error:
        report["status"] = "failed"
        report["error"] = f"{type(error).__name__}: {error}"
        raise
    finally:
        report["finished_at_utc"] = dt.datetime.now(dt.UTC).isoformat()
        json_write(output / "report.json", report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=Path(r"D:\PushTrackML"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.workspace, args.output)


if __name__ == "__main__":
    main()
