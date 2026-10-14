"""Fixed four-beam diagnostic on training-0003; no optimizer or target-based reranking."""
import argparse
from collections import Counter
import datetime as dt
import json
import math
import os
from pathlib import Path
import platform
import shutil
import time

from continue_pilot import OfficialTokenizer
from prepare_pilot import digest, json_write
from train_corpus import DATA, generate, lexical_f1, padded_batch
from train_pilot import encode_row, file_sha256

MODEL_SHA = "34d66789185036a95c84cb1dd3c169cd2f8b8ba111ad31685d08b099b7738365"
REPORT_SHA = "4749bc3efc57530589679f31934d974af6675906b1c56e210b855164e816b4e5"
REVIEW_SAMPLE_SHA = "591af183927318e7c1107cfd4ab10bce72d3a1d99ac7695aa91c06db627fd1f2"
BEAMS = 4
BATCH_SIZE = 8


def decode_candidate(ids, score, tokenizer):
    if not math.isfinite(score):
        raise ValueError("Non-finite beam score")
    ended = tokenizer.eos_token_id in ids[1:]
    if ended:
        ids = ids[:ids.index(tokenizer.eos_token_id, 1) + 1]
    text = tokenizer.decode(ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)
    return {"prediction": text, "generated_ids": ids, "eos_emitted": ended,
            "length_normalized_sequence_score": score}


def beam_predictions(model, examples, tokenizer, device):
    import torch

    model.eval()
    results = []
    with torch.inference_mode():
        for offset in range(0, len(examples), BATCH_SIZE):
            rows = examples[offset:offset + BATCH_SIZE]
            tensors = padded_batch(rows, tokenizer.pad_token_id, device)
            generated = model.generate(input_ids=tensors["input_ids"], attention_mask=tensors["attention_mask"],
                do_sample=False, num_beams=BEAMS, num_return_sequences=BEAMS, max_new_tokens=64,
                length_penalty=1.0, early_stopping=False, use_cache=True,
                return_dict_in_generate=True, output_scores=True)
            sequences, scores = generated.sequences.tolist(), generated.sequences_scores.tolist()
            if len(sequences) != len(rows) * BEAMS or len(scores) != len(sequences):
                raise ValueError("Unexpected beam result shape")
            for index, row in enumerate(rows):
                candidates = [decode_candidate(ids, score, tokenizer) for ids, score in
                              zip(sequences[index * BEAMS:(index + 1) * BEAMS], scores[index * BEAMS:(index + 1) * BEAMS])]
                if any(a["length_normalized_sequence_score"] < b["length_normalized_sequence_score"] - 1e-6
                       for a, b in zip(candidates, candidates[1:])):
                    raise ValueError("Expected model-ranked beam candidates")
                # The original subject is used only to compute evaluation metrics.
                # Never select a candidate by reference agreement or assistant review.
                chosen = candidates[0]
                results.append({"repo_id": row["repo_id"], "commit_id": row["commit_id"], "target": row["target"],
                    **chosen, "exact_match": chosen["prediction"] == row["target"],
                    "lexical_f1": lexical_f1(chosen["prediction"], row["target"]), "candidates": candidates})
            if offset == 0 or (offset // BATCH_SIZE + 1) % 25 == 0:
                print(f"Four-beam generation: {len(results)}/{len(examples)}", flush=True)
    return results


def summarize(predictions):
    if not predictions:
        raise ValueError("Expected predictions")
    counts = Counter(row["prediction"] for row in predictions)
    return {"examples": len(predictions), "exact_matches": sum(row["exact_match"] for row in predictions),
            "mean_lexical_f1": sum(row["lexical_f1"] for row in predictions) / len(predictions),
            "eos_emitted": sum(row["eos_emitted"] for row in predictions),
            "single_line_at_most_72_chars": sum(bool(row["prediction"].strip()) and len(row["prediction"]) <= 72
                and "\n" not in row["prediction"] and "\r" not in row["prediction"] for row in predictions),
            "unique_predictions": len(counts), "most_common_predictions": counts.most_common(5)}


def run(workspace, output):
    if platform.system() != "Windows":
        raise RuntimeError("Run dataset/model diagnostics natively on Windows")
    if output.exists():
        raise ValueError("Preserve previous evidence; output must be new")
    os.environ.update(HF_HUB_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1", CUBLAS_WORKSPACE_CONFIG=":4096:8",
                      HF_HOME=str(workspace / ".cache" / "huggingface"), TEMP=str(workspace / ".tmp"), TMP=str(workspace / ".tmp"))
    import torch
    from transformers import T5ForConditionalGeneration
    from transformers.utils import logging as transformers_logging

    transformers_logging.disable_progress_bar()
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA required; no CPU fallback")
    torch.manual_seed(42)
    torch.use_deterministic_algorithms(True)
    torch.set_float32_matmul_precision("highest")
    torch.backends.cudnn.benchmark = False
    torch.set_num_threads(4)
    prior = workspace / "runs" / "training-0003"
    corpus = workspace / "data" / "corpus-0001" / "audit-0002" / "post-review-pending"
    review_path = prior / "quality-comparison-0001" / "sample.json"
    pinned = {prior / "report.json": REPORT_SHA, prior / "checkpoint" / "model.safetensors": MODEL_SHA,
              review_path: REVIEW_SAMPLE_SHA, corpus / "validation.jsonl": DATA["validation"][1],
              corpus / "train.jsonl": DATA["train"][1]}
    for path, expected in pinned.items():
        if file_sha256(path) != expected:
            raise ValueError(f"Changed frozen artifact: {path.name}")
    protected = json.loads(review_path.read_text())["input_artifacts"]
    for name, expected in protected.items():
        if file_sha256(Path(name)) != expected:
            raise ValueError(f"Changed prior artifact: {Path(name).name}")
    protected.update({str(path): value for path, value in pinned.items()})
    review_file = prior / "quality-comparison-0001" / "review.json"
    review_sha = "addb483b97465318869a34894123d00d1e0e5e075e8cf319ab23bd08ada071d7"
    if file_sha256(review_file) != review_sha:
        raise ValueError("Changed prior semantic review")
    protected[str(review_file)] = review_sha
    rows = [json.loads(line) for line in (corpus / "validation.jsonl").read_bytes().splitlines()]
    if len(rows) != 962 or any(row["split"] != "validation" for row in rows):
        raise ValueError("Expected the frozen validation split")
    adapter = OfficialTokenizer(workspace / "checkpoints" / "codet5-small")
    examples = [encode_row(row, adapter) for row in rows]
    for row, example in zip(rows, examples):
        if digest(row["diff"].encode()) != row["diff_sha256"] or (len(example["input_ids"]), len(example["labels"])) != (row["input_tokens"], row["target_tokens"]):
            raise ValueError("Changed diff or token encoding")
    baseline = json.loads((prior / "final.json").read_text())["generation"]["validation"]
    if [r["commit_id"] for r in baseline["predictions"]] != [r["commit_id"] for r in rows] or [r["target"] for r in baseline["predictions"]] != [r["message"] for r in rows]:
        raise ValueError("Baseline identity/target mismatch")
    output.mkdir(parents=True)
    (output / "provenance").mkdir()
    for name in ("compare_decoding.py", "test_compare_decoding.py", "train_corpus.py", "train_pilot.py", "continue_pilot.py", "compare_tokenizers.py", "prepare_pilot.py", "requirements-train.lock"):
        shutil.copyfile(Path(__file__).parent / name, output / "provenance" / name)
    report = {"status": "running", "started_at_utc": dt.datetime.now(dt.UTC).isoformat(),
        "checkpoint_sha256": MODEL_SHA, "validation_examples": 962, "optimizer_updates": 0,
        "input_artifacts": protected, "source_sha256": file_sha256(Path(__file__)),
        "policy": {"num_beams": BEAMS, "num_return_sequences": BEAMS, "max_new_tokens": 64, "length_penalty": 1.0,
                   "early_stopping": False, "do_sample": False, "selected_candidate": "model rank 1; never reference-ranked"},
        "scope": "Development decoding diagnostic only; no hyperparameter grid, retraining or deployment claim"}
    json_write(output / "report.json", report)
    try:
        model = T5ForConditionalGeneration.from_pretrained(str(prior / "checkpoint"), local_files_only=True,
                    use_safetensors=True, attn_implementation="eager").to("cuda")
        reproduced = generate(model, examples[:16], adapter.tokenizer, "cuda")["predictions"]
        if reproduced != baseline["predictions"][:16]:
            raise ValueError("Greedy baseline reload mismatch")
        report["greedy_reload_predictions_reproduced"] = 16
        torch.cuda.synchronize()
        started = time.perf_counter()
        predicted = beam_predictions(model, examples, adapter.tokenizer, "cuda")
        torch.cuda.synchronize()
        report["beam_generation_seconds"] = time.perf_counter() - started
        json_write(output / "beam4.json", {"metrics": summarize(predicted), "predictions": predicted})
        report["greedy_metrics"] = summarize(baseline["predictions"])
        report["beam4_metrics"] = summarize(predicted)
        report["changed_top1_predictions"] = sum(a["prediction"] != b["prediction"] for a, b in zip(baseline["predictions"], predicted))
        report["reference_found_in_any_of_four_diagnostic_only"] = sum(any(c["prediction"] == row["target"] for c in row["candidates"]) for row in predicted)
        indexed = {row["commit_id"]: row for row in predicted}
        old_sample = json.loads(review_path.read_text())
        selected = [{**row, "beam4_prediction": indexed[row["commit_id"]]["prediction"],
                     "beam4_candidates": indexed[row["commit_id"]]["candidates"]} for row in old_sample["samples"]]
        json_write(output / "paired-sample.json", {"scope": "Same twenty already reviewed development cases; not a blind test",
                  "rubric": old_sample["rubric"], "samples": selected})
        for name, expected in protected.items():
            if file_sha256(Path(name)) != expected:
                raise ValueError(f"Artifact changed during inference: {Path(name).name}")
        report.update(status="completed", input_artifacts_unchanged=True, beam4_sha256=file_sha256(output / "beam4.json"),
                      paired_sample_sha256=file_sha256(output / "paired-sample.json"))
    except Exception as error:
        report.update(status="failed", error=f"{type(error).__name__}: {error}")
        raise
    finally:
        report["finished_at_utc"] = dt.datetime.now(dt.UTC).isoformat()
        json_write(output / "report.json", report)
    print(json.dumps({key: value for key, value in report.items() if key != "input_artifacts"}, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=Path(r"D:\PushTrackML"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.workspace, args.output)
