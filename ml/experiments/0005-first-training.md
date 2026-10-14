# Experiment 0005: first CodeT5-small fine-tuning run

Date: 2026-10-05. The user approved the pinned model download and at most 100
optimizer steps. Everything ran on **native Windows, RTX 4070**. This was a
local research/learning exercise, not training from scratch or product release.

## Outcome

**The training loop works, but the tiny model adaptation overfits.** Exactly
100 optimizer updates completed. No extra training or validation-driven tuning
was performed after inspecting the result.

| Metric | Pretrained baseline | After 100 steps |
| --- | ---: | ---: |
| Training token-weighted loss, 11 examples | 9.527922 | 0.256093 |
| Validation token-weighted loss, 5 examples | 8.219109 | 8.989712 |
| Exact reference subjects, training | 0/11 | 8/11 |
| Exact reference subjects, validation | 0/5 | 0/5 |

Loss is mean token-level cross-entropy using the reference preceding tokens
(teacher forcing). Baseline and final loss both use evaluation mode, so dropout
is disabled. The separately logged per-step training losses include dropout
and different sampled examples; they are not directly interchangeable with
these aggregate losses.

A low teacher-forced loss does not guarantee good autoregressive generation.
For example, the trained model correctly reproduces **"Fix the instance mode
assignment for the head block"** on its training example, but emits **"Remove
the Gaussian Approximation warning"** for several unrelated diffs. Four of five
validation predictions repeat that warning-removal subject; the remaining one
repeats a different training subject. One training prediction also repeats
"year" instead of completing the intended date-construction message.

This is evidence of memorization and poor generalization on this tiny check,
not a useful commit-message model. Exact string matching alone is not a quality
metric—alternative subjects can be valid—but these observed unrelated subjects
are genuine qualitative failures. Five validation rows cannot support a broad
statistical conclusion about CodeT5 itself.

## Environment and checkpoint

- Python **3.12.8**, PyTorch **2.14.1+cu130**, CUDA runtime **13.0**,
  Transformers **5.18.0**.
- Separate **`D:\PushTrackML\.venv-train`**, with 35 hash-locked packages.
  The existing CUDA-proof `.venv` and data `.venv-data` were not synchronized
  against the new lock or changed. Cached torch packages were reused.
- `Salesforce/codet5-small` revision
  `b1ee9570c289f21b5922b9c768a1ce12957bf968`.
- Downloaded **242,026,427 bytes** once. SHA-256:
  `968fb0f45e1efc8cf3dd50012d1f82ad82098107cbadde2c0fdd8e61bac02908`.
- Loaded with explicit `torch.load(..., weights_only=True)`, tensor-only state
  validation, and `load_state_dict(..., strict=True)`. No remote model code,
  permissive pickle fallback, or partially random checkpoint loading.
- Actual parameter count: **60,492,288**, all trainable. This is full-parameter
  fine-tuning, not LoRA or a newly trained tokenizer.

The card's research-use wording and unresolved product-distribution licensing
remain as documented in experiments 0003/0004. This run does not resolve them.

## Fixed recipe

| Setting | Value |
| --- | --- |
| Data | Existing assistant-curated 11 train / 5 validation examples |
| Seed | 42 |
| Optimizer | AdamW, lr 0.0005, weight decay 0.01 |
| Betas / epsilon | (0.9, 0.999) / 1e-8 |
| Batch size / updates | 1 / exactly 100 |
| Sampling | Seeded shuffle each epoch; one example seen 10 times, ten seen 9 times |
| Gradient clipping | Norm 1.0; stop on non-finite loss/gradient |
| Scheduler / mixed precision | None / none; float32 |
| Attention / numerical settings | Eager; deterministic algorithms; highest float32 matmul precision |
| Input | `summarize changes: ` followed only by the complete diff |
| Target | Reviewed English subject, including tokenizer BOS/EOS |
| Token limits | 512 input / 64 target; reject, never truncate |
| Padding | None, because batches contain one unpadded example |
| Generation | Greedy, one beam, no sampling, at most 64 new tokens |

Commit identities, provenance, and target messages never enter the encoder
input. Validation examples were evaluated before/after but received **zero
optimizer updates**. No hyperparameter search or checkpoint selection used
validation results. These are validation data, not an independent test set.

The source dataset, curation, source-permission screening, and limited
repository/fork/near-duplicate checks are recorded in experiment 0004. Nine of
16 subjects are explicit assistant annotations, not independent human labels.
No new corpus or tokenizer assets were downloaded for this training run.

Run timestamps: **10:50:02.518730-10:50:37.666487 UTC**. The 100-update loop took
**10.095 seconds**; the complete baseline/train/final/save run took about
**35.15 seconds**, excluding installation and the earlier download. This timing
is specific to 11 short examples on an RTX 4070, not a CPU inference benchmark.

## Saved evidence and verification

```text
D:\PushTrackML\checkpoints\codet5-small\acquisition.json
D:\PushTrackML\runs\training-0001\
    report.json
    baseline.json
    steps.jsonl
    final.json
    verification.json
    provenance\
    checkpoint\model.safetensors
```

The final safetensors file is **241,984,552 bytes**. SHA-256:
`2342772851b35ac4875423af0dfbc591407fa1b4efbcd48737dd32cbe3dc401c`.
Its file size is not measured runtime RAM or a compression result.

A fresh Windows process reloaded the saved safetensors and official tokenizer
offline, reproduced all 16 generated outputs and both final losses, and made
**zero additional optimizer updates**. It verified all 100 logged training
identities against the training split, no validation updates, changed embedding
weights, checkpoint/data hashes, and three unchanged earlier artifact hashes.

**43 offline tests passed:** eight focused training tests in `.venv-train` and
35 existing data/tokenizer regressions in `.venv-data`. The initial test fixture
needed correction for Transformers' lazy imports before the download; the
actual training run completed once without a retry. The saved-checkpoint reload
is a separate inference check, not a second complete training run.

Run report SHA-256:
`3433921f6e3cdde82e7a4d408eeb8e8e10da4fe0c4e285f40a87df1973bee29e`.
Executed trainer SHA-256:
`e82266f664e12c3a55266450e1df90c86c2e56f00eeeb38fe479dd111882530a`.

## Reproduction and scope

With the existing reviewed Windows data/assets, from `experiment/`:

```powershell
.\setup-windows.ps1 -Workspace 'D:\PushTrackML' -Training
& 'D:\PushTrackML\.venv-train\Scripts\python.exe' -m unittest -v test_train_pilot

# Only for a separately approved rerun; never overwrite training-0001:
& 'D:\PushTrackML\.venv-train\Scripts\python.exe' .\train_pilot.py `
    --workspace 'D:\PushTrackML' --output 'D:\PushTrackML\runs\training-new'
```

The trainer enforces native Windows, available CUDA, pinned input hashes, a new
output directory, and the 100-step cap. The setup script's `-Training` and
`-DataPreparation` switches are mutually exclusive. Do not synchronize either
older environment against `requirements-train.lock`.

A truthful experience claim is: **implemented and ran a pinned native-Windows
CodeT5 fine-tuning pipeline with source-traceable diff/subject pairs, validation
separation, safe checkpoint loading, and documented overfitting.** Do not claim
production-quality messages, broad held-out performance, compressed deployment,
small CPU RAM use, or a working publish feature. Rust code, folder settings, and
Git commit/push behavior were not changed; no commit or push was performed.
