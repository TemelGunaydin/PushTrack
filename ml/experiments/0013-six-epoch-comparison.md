# Experiment 0013: bounded six-epoch full-set comparison

Date: 2026-10-11. **Completed and verified**, including the primary semantic
review and an explicitly post-run secondary review. Native training ran
**14:07:57.847619–14:34:50.966332 UTC**; the controller exited **0** at 14:34:51.
Thirty-six focused native-Windows tests passed before launch. Exactly six epochs
completed; no further training followed.

**The longer recipe did not establish a reliable semantic improvement.** The
predeclared loss-selection rule picked its epoch 3, not epoch 6. Some property
and TODO summaries improved, but serious mistakes—including blacklist becoming
whitelist—remain. No checkpoint was promoted into the application.
The user authorized continued model-quality improvement. Experiment 0012 did
not support adopting four-beam decoding; its small training-only review found
both useful references and concrete label weaknesses. Neither that sample nor
the old decaying-LR plateau isolates the cause of model errors. This is one
controlled longer recipe, not a claim that more epochs will solve everything.

## Fixed recipe and stopping rule

- Start from the **original pretrained CodeT5-small** checkpoint, SHA-256
  `968fb0f45e1efc8cf3dd50012d1f82ad82098107cbadde2c0fdd8e61bac02908`.
  Do not resume or overwrite training-0001/0002/0003.
- Keep all **9,758 training / 962 validation** rows unchanged, including original
  subjects and pending-quality flags. Even newly diagnosed label weaknesses are
  recorded separately, not silently rewritten between compared recipes.
- Exactly **six full epochs**, batch **8**, independent shuffle seeds **42–47**;
  retain each final six-row batch: **7,320 updates / 58,548 training exposures**.
- AdamW max LR **5e-5**, weight decay 0.01, betas (0.9, 0.999), epsilon 1e-8,
  norm clipping 1.0. **366 warmup updates** then the existing positive-ending
  linear decay across the whole 7,320-update budget.
- Full-parameter float32/eager training on native Windows CUDA. Same pinned
  environment, official tokenizer, complete inputs, prefix, and 512/64 limits.
- Measure full train/validation teacher-forced loss and all validation greedy
  generations after every epoch. Retain the same 64 train-generation cases.
- **Stop after epoch six**, with no early stop, extra epoch, automatic retry,
  learning-rate search, data acquisition, or new-model download.
- Preserve all six checkpoints. Select the checkpoint with the **lowest full
  validation loss**, breaking exact ties in favor of the earlier epoch, then
  review its semantic outputs. Preserve/report epoch six separately even if it
  is not selected. No target-based candidate reranking or selection by the
  twenty known semantic cases. Validation informs checkpoint selection but
  **never backward/optimizer updates**; the test split remains untouched.

This changes both the update budget and its scaled warmup/decay, and introduces
predeclared validation-based checkpoint selection. It compares **recipes**, not
only epoch count. Lowest validation loss does not certify semantic faithfulness.

## Artifacts and verification plan

New output: `D:\PushTrackML\runs\training-0004`. All prior runs remain intact.

The declared proof covered per-epoch losses/generations, orders/exposures, exact
source/checkpoint hashes, controller status and timing, plus fresh selected/final
checkpoint reloads. Semantic review uses the same twenty already inspected full
diffs, not a new blind benchmark.

## Actual measurements

| Stage | Full train loss | Full validation loss | Validation lexical F1 | Exact matches |
| --- | ---: | ---: | ---: | ---: |
| Previous three-epoch recipe, final | 2.419144 | 3.126153 | 0.222125 | 0/962 |
| New epoch 1 | 2.792362 | 3.211624 | 0.204229 | 0/962 |
| New epoch 2 | 2.433584 | 3.123558 | 0.221644 | 0/962 |
| **New epoch 3: loss-selected** | **2.192909** | **3.118129** | **0.221487** | **0/962** |
| New epoch 4 | 2.016537 | 3.144040 | 0.221763 | 2/962 |
| New epoch 5 | 1.903054 | 3.176025 | 0.229264 | 2/962 |
| New epoch 6: final | 1.857100 | 3.189596 | 0.228932 | 1/962 |

The entire original pretrained baseline reproduced exactly. Every one of the
9,758 training identities appeared **six times**, totaling **58,548 exposures**
and **7,320 updates**; all 60,492,288 parameters were trainable. No validation
identity appeared in an optimizer update.

The new epoch 3 is **not the old three-epoch checkpoint**: the six-epoch schedule
has a longer warmup and more remaining LR at that point. Lowest validation loss
improved only slightly versus the previous recipe. After the new epoch 3,
validation loss worsened while train loss kept falling—an overfitting signal
for this recipe and these references, not proof that no other training can help.
Lexical overlap and exact matches did not move in lockstep with teacher-forced
loss; none of these metrics certifies semantic correctness.

Selected epoch 3: 962/962 EOS, 962/962 short single-line subjects, 953 distinct
outputs. Final epoch 6: 962/962 EOS, 960/962 short single-line subjects, 957 distinct
outputs. Training loops totaled **944.141 seconds**; complete trainer duration
was **1,613.119 seconds**. Peak CUDA tensor allocation: **3,019,839,488 bytes**;
reservation: **3,672,113,152 bytes**. These are not CPU process-RAM measurements.

## Fresh-process proof and provenance

Verification passed at **14:35:16 UTC**:

- Independently reconstructed seeds 42–47, every batch, all 7,320 LR/gradient/
  training-mode records, six exposures each, and all final six-row batches.
- Checked all six safetensors hashes and every epoch's active-token-weighted
  loss accounting and prediction identities. Full original baseline equality
  passed, not merely its rounded aggregate metrics.
- Independently confirmed that minimum validation loss selects **epoch 3**.
- Freshly reloaded **epoch 3 and epoch 6**, each reproducing the first **16** saved
  validation predictions and both original padded-batch losses within `1e-6`.
  Verified saved-tokenizer parity and changed embeddings versus pretrained
  weights. Other checkpoints were hashed, not separately reloaded.
- Checked **35 protected input/historical artifacts**, including old learning
  files/models, frozen corpus, prior reviews and the decoding diagnostic.
- Verification performed **zero optimizer updates**.

Weights are 241,984,552 bytes per checkpoint:

| Artifact | SHA-256 |
| --- | --- |
| Epoch 1 | `b5bca03c09949bc58cb3c02e4b8f8f64a55f62a4fcf6ae4a5a0a1f0abc03f3f2` |
| Epoch 2 | `43a9cd0c7f9a39491b213f283f5a7004b18e4eaaebe8b1ea6b23fc337765d076` |
| **Epoch 3: selected** | `79aeae15958f3c81c201489107178b66b3d6b7e24a698e3e0551d66360414abc` |
| Epoch 4 | `9623526c794c3295623b06d1f8bc51968d49a16324899a3829b54d4a2c06576b` |
| Epoch 5 | `f48f6f3d68174c147221445bad6c1f9f7d01c69cde197302d81e31e31aa44470` |
| Epoch 6: final | `b497f043d7d203bf2a66b42784d9c022e5c6d6b4e9f93ed4bb2905dcbb45fa3a` |
| Executed trainer | `f9718c9f0309c8d3e2a738462fa970ba1215e5252aad14e2ee1953822d6cba77` |
| Trainer tests | `d54a666cf3c2df989220900f0211d7a7f7f167d40664d2439148b355e433de7d` |
| Completed report | `00085dd18cb3d717a80a56b3a8cbe0cba45567a0e247847a0339a7fb120d2177` |
| Step log | `0fb4ce6e2839a5204f3b9ce0586c4a889934851c45a7b50c149d7a52b2342f01` |
| Executed verifier | `fcbc808e3c74942ab2c6d2d685c1a25e2e7e31e0077894635a568319f1f85585` |

The trainer retains one epoch as its default and the old three-epoch recipe;
only explicit `--epochs 6` invokes the new fixed recipe and selection policy.
There is no arbitrary epoch-count mode, optimizer-state resume, or extension.

## Semantic review and post-run secondary analysis

The **primary** review examined the loss-selected epoch 3 under the existing
rubric. After observing divergence between loss and lexical metrics, a
**post-run secondary** review of the final epoch 6 was explicitly added before
reading its twenty output subjects. It is not a replacement for the predeclared
selection rule or a blind confirmatory test. `report.json` still selects epoch 3.

| Same 20 development cases | Previous three-epoch final | New selected epoch 3 | New final epoch 6 (secondary) |
| --- | ---: | ---: | ---: |
| Usable | 6 | 5 | 6 |
| Needs edit | 7 | 9 | 8 |
| Misleading | 7 | 6 | 6 |

These are **unblinded assistant judgments**, not independent human annotation or
population accuracy. **Nine selected-model and ten final-model judgments** are
interpretation-sensitive. Their reasons are stored per case. No original labels
or older judgments were changed, and no best-of-candidates/reference-based
reranking was used.

Examples from the same complete diffs:

- **Property types improve:** final epoch 6 names drag-indicator wrapper typings
  instead of inventing methods. The selected checkpoint only says missing
  properties and remains too generic.
- **Comment versus behavior improves in one case:** both new checkpoints
  correctly describe adding TODO; the older model claimed a syntax fix.
- **Opposite behavior remains:** final epoch 6 says **add whitelist for cnki**, but
  the diff adds cnki patterns to `pdfBlacklist` and leaves `pdfWhitelist` empty.
- **Wrong direction remains:** selected epoch 3 claims an activation pattern now
  includes `**/`; the diff removes that prefix from pyright activation and adds
  a different root-level config entry.
- **Addition versus modification remains:** final epoch 6 says **Add iconAlign
  to button props** even though that property already exists and only its
  documentation changes. Holiday-label correction is still called an added
  holiday.
- **Reference ambiguity matters:** terse JS-file additions can mean manifest
  entries or actual new files; testing removal can mean local usage or flag
  deletion. These cases are flagged rather than treated as definitive scores.

The review preservation proof passed at **14:45:18 UTC**: 20 unique development
cases, 40 new model assessments, **51 protected artifacts unchanged**, zero
updates and zero dataset changes. This verifies identities/counts/preservation,
not the semantic judgments independently.

| Review artifact | SHA-256 |
| --- | --- |
| Primary paired sample | `825382a8f409e1f493428a22627b7ce48ad7cd119724d7c1e2bd1a61b139f129` |
| Final-epoch secondary evidence | `b717f35a26baa4ded5aa184e3c6cd906cc35d6feb58a9287ad617f1a70272267` |
| Combined annotations | `0d1b7eceb6f0382e64c508728d3484253f1bf0a542cd5fe48a8a3ed1fed1ef2a` |

## Conclusion and stop condition

The bounded longer run is complete. It produces some better descriptions but
also new errors; neither the primary candidate nor the secondary final model
establishes a reliable overall improvement. **Do not keep adding epochs or
promote either checkpoint automatically.** The next useful intervention is
traceable, training-only target-quality work, preserving full diffs and original
subjects in a separate proposed data version. This is a supported direction for
further research, not a guarantee that label repair alone will solve model
capacity, grounding or generalization limitations.

No CPU deployment profiling, dataset/label rewrite, Rust integration, compression,
commit, or push is included. Most labels and many repository identities remain
unreviewed; distribution licensing and source/privacy/pretraining-overlap risks
remain unresolved. No production model promotion follows automatically.
