# Experiment 0009: full-dataset research fine-tuning

Date: 2026-10-05. **Completed and independently reloaded.** The native Windows
trainer ran **17:24:16.097339–17:31:25.944107 UTC**; the controller exited zero
at 17:31:26 UTC. All **1,220 updates** completed, covering every one of the
**9,758 training examples exactly once**. Validation loss improved, but exact
validation-subject matches remain 0/962; this is not a production-readiness claim.

The user explicitly requested training after discussion of the remaining label
and fork-family limitations. This authorizes a bounded research experiment on
the existing data, not retrospective certification of every training label.
Original pending-data manifests and review flags remain unchanged. No further
GitHub metadata lookup, data acquisition, model download, or package installation
is part of this run. The test split remains untouched.

## Fixed inputs

- Existing `audit-0002/post-review-pending`: **9,758 train / 962 validation**.
- Complete, losslessly tokenized original diffs and original English-subject
  candidates; known quality holds remain excluded, with no replacement rows.
- Train SHA-256:
  `5dd4d286b73bea89456bdb2cb3c5cb23a3757ad38a6baaa37099fe5f0a4d4269`.
- Validation SHA-256:
  `76b9d83b60741738c29dc53f8629ec4c0e08434427595a5191682f19f42ba2ee`.
- Original pretrained `Salesforce/codet5-small`, revision
  `b1ee9570c289f21b5922b9c768a1ce12957bf968`; existing weights SHA-256
  `968fb0f45e1efc8cf3dd50012d1f82ad82098107cbadde2c0fdd8e61bac02908`.
- **Not** the memorized 100-step adaptation in `training-0001`.

`train_corpus.py` reuses the official tokenizer, encoder-only diff contract,
weights-only safe loading, strict state-dictionary checks, and original model
assets from the earlier trainer. It neither changes nor generalizes away the
old tiny trainer's 11/5 hash lock. New outputs must not already exist.

## Fixed recipe, selected before measurements

- All **60,492,288 parameters** trainable, native Windows CUDA / RTX 4070.
- **One complete epoch**, not another 100-step demonstration: every training
  example exactly once in seeded shuffled order. No convergence claim.
- Batch size **8**, **1,220 optimizer steps**; final six examples are retained.
- AdamW maximum learning rate **0.00005**, betas `(0.9, 0.999)`, epsilon `1e-8`,
  weight decay `0.01` on all optimizer parameters.
- **61 warmup steps**, then linear decay; the final actual update still has
  positive learning rate. No validation-based learning-rate or epoch selection.
- Gradient clipping at `1.0`; fail before updates on non-finite loss/gradients.
- Seed **42**, deterministic float32/eager attention, four CPU threads; no AMP,
  quantization, LoRA, scheduler search, or silent CPU fallback.
- Dynamic right padding: input padding masked, target padding **-100** excluded
  from the loss. Preserve complete **512/64** token limits with no truncation.
- Encoder receives only `summarize changes: ` plus the diff. Identity, target,
  and review metadata never enter the encoder.

## Measurements and regression tests

Before and after the fixed epoch:

- Full **9,758-example train** and **962-example validation** target-token-weighted
  teacher-forced cross-entropy, including recorded BOS/EOS labels.
- Greedy, one-beam, non-sampling generation with at most 64 new tokens for **all
  962 validation examples**, plus the same deterministic **64-example training
  sample**. Training generation metrics do not describe all 9,758 examples.
- Exact reference matches, case-folded token-overlap F1, EOS/subject-length
  diagnostics, and repeated-output counts. These are not semantic accuracy.

Only training examples enter backward/optimizer operations. Validation is
measurement-only. The final checkpoint is saved in safetensors immediately after
training, before final measurement, so a later evaluation failure cannot erase
the completed training result. Fresh-process reload and reproduction succeeded
as detailed below.

**20 focused Windows tests passed**: 12 corpus-training tests and the eight
previous safe-loading/tiny-training tests. New coverage includes full-epoch
coverage without dropped/repeated rows, nonzero final learning rate, input/label
padding, fixed data hashes/status, recorded token lengths, cross-split identities,
active-token loss weighting, and target-free generation.

## Observed results

| Metric | Original pretrained model | After one complete epoch |
| --- | ---: | ---: |
| Full train token-weighted loss (9,758 rows) | 8.654269 | 2.898312 |
| Full validation token-weighted loss (962 rows) | 8.699134 | 3.219000 |
| Train-sample exact matches (64 rows) | 0/64 | 2/64 |
| Validation exact matches | 0/962 | 0/962 |
| Validation mean lexical token F1 | 0.012393 | 0.203403 |
| Validation EOS emitted | 214/962 | 962/962 |
| Validation nonempty single-line output <=72 characters | 9/962 | 962/962 |
| Distinct validation outputs | 898 | 937 |

The optimizer loop took **158.773 seconds**; loading, both measurement passes,
training, and saving together took **429.847 seconds**. These are this machine's
observed run times, not CPU deployment latency. Peak CUDA tensor allocation was
**3,014,151,680 bytes**, and peak allocator reservation **3,670,016,000 bytes**;
neither is total process RAM or complete device-memory usage.

The pretrained baseline often emitted denoising sentinel-like strings and
repetition rather than commit subjects. Fine-tuning learned the requested output
form and improved loss/token overlap on the current validation split. However,
short, fluent output is not necessarily specific or faithful. Exact match also
penalizes valid paraphrases, so 0/962 exact matches does not mean every output is
wrong, while the loss/F1 improvements do not prove every output is correct.

Six deterministic prediction comparisons (`result-sample-42` ordering) included:

- Reference `Add codeql-path to README (wip)` -> generated
  `Add codeql path to readme`: similar wording without exact equality.
- Reference `Avoid triggering undefined behaviour in base_uint<BITS>::bits()`
  -> `Fix bug in uint256`: noticeably less specific wording.
- Reference `feat: add pseudo prop typings` ->
  `Add actionsheet props to actionsheet`: repetitive, weakly specific wording.

These are output/reference comparisons, **not a diff-grounded semantic quality
score** or independent human assessment. No extra epochs, decoding search, or
post-hoc target rewriting were performed to improve the reported numbers.

The subsequent [twenty-diff assistant review](0010-model-quality-review.md)
judged 3 outputs usable, 12 needing edits, and 5 misleading. It records semantic
failure cases and reference limitations without changing this run or its data;
these unblinded sample counts are not global accuracy.

## Fresh-process verification

At **17:33:01.619923 UTC**, `pushtrack-verify-corpus-training.py` passed:

- Independently reconstruct seed-42 order and verify all 1,220 step records,
  every training identity exactly once, final six-row batch, finite positive
  gradient norms, and the fixed learning-rate schedule.
- Confirm **zero validation updates** and recompute full active-token loss
  accounting and exact-match counts from saved measurements.
- Verify saved safetensors size/hash, reload offline in a fresh Windows process,
  and confirm saved-tokenizer IDs against the original adapter.
- Reproduce the **first 16 validation predictions** exactly, in their original
  two padded batches; corresponding batch losses matched within `1e-6`.
  This is a 16-example reload proof, not a second full-validation run.
- Verify changed model embeddings against the original pretrained checkpoint.
- Reconfirm unchanged current dataset/manifest hashes, old 11/5 learning files,
  old training report, and old checkpoint. Pending quality flags stay false.
- Verification performed **zero optimizer updates**.

Hashes:

- Executed trainer:
  `0e0ad0c750ba0c5c93b30e7f723d23e6b96040df945f19186dffae5b036bc123`.
- New `model.safetensors` (**241,984,552 bytes**, weights only):
  `3faa0dd2f9ad78ab4d9eab5e78cd4a1d7fbfe21521bff6a991d7ebf7a119d81f`.
- Completed report:
  `f41c5265cb8f61f4a1dfeb376a907e501a044cea2d39ff8b62f5fb51d67af3e5`.
- Step log:
  `687113e3624e9fd5dfad874ac20f63a5042df87f60dc5a7a16c88774dbeb8437`.
- Executed verifier:
  `fe51a19b7d761767e72053e86a3f048d9ddf1068afb38de5b325da9c5f4890e6`.

## Artifacts

```text
D:\PushTrackML\runs\
    training-controller-0002.json
    training-0002.stdout.log
    training-0002.stderr.log
    training-0002\
        report.json
        baseline.json
        steps.jsonl
        final.json
        verification.json
        checkpoint\
        provenance\
```

Run with the existing `.venv-train`, not a newly synchronized environment:

```powershell
# Only for this explicitly authorized run and a NEW output path.
& 'D:\PushTrackML\.venv-train\Scripts\python.exe' -u .\train_corpus.py `
    --workspace 'D:\PushTrackML' --output 'D:\PushTrackML\runs\training-0002'
```

The recorded command has finished. Do not rerun it or extend training
automatically; its output-exists guard intentionally preserves this result.
No auto-resume, automatic further epoch, commit, push, Rust behavior change,
compression, deployment, or publish command is authorized by this experiment.

## Interpretation limits

Most labels are unreviewed original-subject weak supervision; current canonical
fork metadata covers 51/244 repositories. Exact/stable-patch and defined
near-change screens passed, but detached copies, complete family separation,
pretraining contamination, and exhaustive legal/privacy clearance are unresolved.
Any observed validation improvement is preliminary evidence under this split,
not proof of uncontaminated generalization. CodeT5 product-distribution license
wording remains unresolved. CPU inference RAM and deployment suitability are not
measured by this CUDA training run.
