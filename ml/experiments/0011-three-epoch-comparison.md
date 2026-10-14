# Experiment 0011: fixed three-epoch comparison

Date: 2026-10-11. **Completed and verified**, including the paired development
review. Native training ran **10:59:32.546653–11:14:41.023106 UTC** and the
controller exited zero at 11:14:41.791706 UTC. Exactly **3,660 updates** completed.
This was a new run from original pretrained weights, not a resume of
`training-0002`. That run and its twenty-example review are preserved.

Validation loss improved modestly, but semantic changes were mixed: the same
20-case assistant review found **6 usable / 7 needing edits / 7 misleading**,
versus **3 / 12 / 5** previously. Do not interpret these unblinded sample counts
as population accuracy or declare the model production-ready.

## Scope and predeclared recipe

- Existing **9,758 train / 962 validation** files from
  `data/corpus-0001/audit-0002/post-review-pending`, with unchanged pinned hashes.
- Existing original CodeT5-small weights at revision
  `b1ee9570c289f21b5922b9c768a1ce12957bf968`, SHA-256
  `968fb0f45e1efc8cf3dd50012d1f82ad82098107cbadde2c0fdd8e61bac02908`.
- All **60,492,288 parameters**, native Windows RTX 4070, float32/eager attention,
  deterministic algorithms and four CPU threads, exactly as in experiment 0009.
- **Three complete epochs**, batch **8**, **3,660 optimizer updates** and
  **29,274 example exposures**. Every training example appears once per epoch;
  the final six-example batch is retained each time.
- Model/dropout seed **42**; independent deterministic shuffle seeds **42/43/44**.
- AdamW maximum LR **5e-5**, betas `(0.9, 0.999)`, epsilon `1e-8`, all-parameter
  weight decay `0.01`, gradient clip `1.0`, non-finite failure guards unchanged.
- **183 warmup steps** (5% of the full budget), then linear decay over the
  remaining global updates. LR is not restarted at epoch boundaries; the final
  actual update remains positive.
- Each epoch saves a safetensors checkpoint before full train/validation loss
  measurement and generation on the same 64 training samples/all 962 validation
  rows. Validation is never used for backward/optimizer updates.
- Choose the **predeclared final epoch**, not a retrospectively selected best
  checkpoint. No early stopping, automatic extension, or optimizer-state resume.
- Compare the previously reviewed 20 validation cases using the same diffs and
  rubric. They are development evidence, not a blind final test.

This is a comparison of **training recipes**, not an isolated causal effect of
adding epochs: the longer run also stretches warmup/decay over three times as
many updates. Its first-epoch weights need not match the old one-epoch run.
Original target-quality flags remain unchanged; the prior explicit research
approval is not independent label certification.

No corpus/model downloads, GitHub metadata requests, credentials, package
changes, test-split reads, Rust integration, compression, commit, or push.

## Implementation and regression proof

`train_corpus.py` retains the old one-epoch default and adds an explicit bounded
`--epochs 3` option. Only one or three epochs are accepted. The training-only
update loop is extracted into `train_epoch`, which restores `model.train()`
after every measurement leaves the model in evaluation mode. Padding, tokenizer,
input/target separation, safe initial loading, and frozen data checks are reused.

**20 existing Windows tests passed before editing; all 26 passed afterward.**
The six added tests cover the three-epoch plan with unchanged first permutation,
rejection of unsupported epoch counts, continuous global LR scheduling, training
mode/gradient restoration after evaluation, and stopping before optimizer updates
on non-finite loss or gradients. Tiny test tensors run on CPU; the actual trainer
still refuses CPU fallback.

- Executed trainer SHA-256:
  `330cff2078196f7d534891ecde0e7307b79ad368d792b8bea40e7ec84f1bab8e`.
- Training tests SHA-256:
  `396a06508ca9b377b5d7f8c235749115f2421656042db1a3985454df2e428f5a`.
- Preflight verified seven pinned inputs/historical artifacts, a new output path,
  **11,645,485,056 free GPU bytes** and **169,611,567,104 free disk bytes**.
- Existing environment: PyTorch **2.14.1+cu130**. No environment synchronization.

## Artifacts and invocation

```text
D:\PushTrackML\runs\
    training-controller-0003.json
    training-0003.stdout.log
    training-0003.stderr.log
    training-0003\
        report.json
        baseline.json
        steps.jsonl
        epoch-1.json
        epoch-2.json
        final.json
        checkpoint-epoch-1\
        checkpoint-epoch-2\
        checkpoint\
        verification.json
        quality-comparison-0001\
            sample.json
            review.json
            verification.json
            provenance\
        provenance\
```

Recorded command, **already completed; do not repeat automatically**:

```powershell
& 'D:\PushTrackML\.venv-train\Scripts\python.exe' -u .\train_corpus.py `
    --workspace 'D:\PushTrackML' --output 'D:\PushTrackML\runs\training-0003' `
    --epochs 3
```

The controller held SSH open while the native child ran, without a service or
scheduled task. Existing output is refused and no automatic retry/resume or
extra epoch was performed.

## Measured results

| Recipe/stage | Full train loss | Full validation loss | Validation exact matches | Validation lexical F1 |
| --- | ---: | ---: | ---: | ---: |
| Original pretrained baseline | 8.654269 | 8.699134 | 0/962 | 0.012393 |
| Previous one-epoch recipe | 2.898312 | 3.219000 | 0/962 | 0.203403 |
| New recipe: epoch 1 | 2.799864 | 3.205978 | 0/962 | 0.201063 |
| New recipe: epoch 2 | 2.524625 | 3.127852 | 0/962 | 0.219594 |
| New recipe: epoch 3 (preselected final) | **2.419144** | **3.126153** | **0/962** | **0.222125** |

Final train-generation sample: 2/64 exact matches (unchanged from the old run),
lexical F1 0.298468 versus 0.227283. These generation counts describe only the
fixed 64 training examples; train loss covers all 9,758.

All 962 final validation predictions emitted EOS; **961/962** were nonempty
single-line outputs within 72 characters, versus 962/962 in the old run. There
were 952 distinct predictions versus 937 previously. Neither fluency, distinct
outputs, nor token overlap proves semantic correctness.

Training loops totaled **470.176 seconds**; the full run took **908.476 seconds**
including baseline, all epoch measurements, and checkpoint writes. Peak CUDA
tensor allocation was **3,014,151,680 bytes**, reserved memory **3,670,016,000
bytes**. These are not CPU process-RAM or total device-memory measurements.

Validation loss barely changed between epochs 2 and 3 while train loss kept
falling. This warrants caution about simply extending training, not a claim
that one small run proves a general overfitting threshold.

## Checkpoint and execution verification

Fresh-process verification passed at **11:14:57.232997 UTC**:

- Reconstructed all three independent shuffles, 3,660 global step/LR records,
  and 29,274 exposures; every training identity appeared exactly three times.
- Verified final six-row batches, finite positive gradient norms, restored
  training mode in every logged update, and **zero validation updates**.
- The entire newly measured pretrained baseline reproduced the saved original
  baseline exactly (loss records and generated predictions), not just a sample.
- Verified all three safetensors checkpoint hashes; freshly reloaded the final
  checkpoint and reproduced the first **16** validation predictions and their
  original two padded-batch losses within `1e-6`. Intermediate checkpoint hashes
  were checked; they were not separately reloaded for full re-evaluation.
- Confirmed tokenizer IDs, changed embeddings versus the original pretrained
  weights, frozen data hashes, old learning/training artifacts, and the original
  twenty-example review. Verification performed **zero optimizer updates**.

Each weight file is **241,984,552 bytes** (weights only):

| Artifact | SHA-256 |
| --- | --- |
| Epoch 1 weights | `cbe19d300041fbf0510d661a1e63e6c3bfa3a2781d808099177474693a0be971` |
| Epoch 2 weights | `2ae625e58433c627bd61ccff2d15a8734df0a861c8411d0f7a41e1b2292b50e4` |
| Final epoch 3 weights | `34d66789185036a95c84cb1dd3c169cd2f8b8ba111ad31685d08b099b7738365` |
| Completed report | `4749bc3efc57530589679f31934d974af6675906b1c56e210b855164e816b4e5` |
| Step log | `7f92fe34bd7a0727f275b118c58082256b9b11fbd16006ee5927e61022cea952` |
| Executed verifier | `d74ed0506e79851c42ccf8a1d9029043107ab51be02ea650c83fac47eb00273b` |

## Paired semantic review: mixed results, not automatic promotion

The assistant reread all **20 complete diffs** from experiment 0010 and compared
the saved one- and three-epoch predictions under the same rubric. No examples
were replaced and no labels were rewritten. This is an **unblinded development
comparison by the same assistant**, not independent human evaluation or a new
held-out test. Seven new judgments are interpretation-sensitive.

| Judgment | One epoch | Three epochs |
| --- | ---: | ---: |
| Usable | 3 | **6** |
| Needs edit | 12 | **7** |
| Misleading | 5 | **7** |

Transitions: three usable subjects stayed usable; three edit-needed subjects
became usable, five stayed edit-needed, and four became misleading. Two earlier
misleading subjects became edit-needed, while three stayed misleading.

| Case from experiment 0010 | Three-epoch subject | Decision |
| --- | --- | --- |
| 1 | Add codeql path to README | Usable: same supported documentation change. |
| 2 | Fix duplicate key check | Usable: same acceptance boundary as before. |
| 3 | fix bug in uint256 | Needs edit: still omits unsigned-mask change. |
| 4 | Fix workspaceContains:mspythonconfig | Needs edit: misses addition detail and pyright activation narrowing. |
| 5 | Add methods to actionsheet content props | **Misleading regression:** optional data props are not methods. |
| 6 | Fix gemspec dependency | Needs edit: no longer falsely adds a dependency, but omits the changed constraint. |
| 7 | Fix test for string contains | Needs edit: awkward/vague assertion replacement. |
| 8 | Fix button icon align | **Still misleading:** only a documentation comment changes. |
| 9 | Added removed changelog for removed lost-cv images | Needs edit: grounded topic, awkward wording. |
| 10 | fix(app-config): add http:// to blacklist | **Misleading, borderline:** actual exclusion is domain-specific cnki.net over HTTP/HTTPS, not the scheme itself. |
| 11 | Add paths to ScssPHP | Usable, borderline: names the actual path addition rather than a generic compiler fix. |
| 12 | Add error handler for CLI | Usable, borderline: accepted as concise error-reporting/Click-integration shorthand. |
| 13 | add infotip and tourtip to browser.json | Usable: identifies both actual new mappings. |
| 14 | fix(i18n): add namespace to useTranslation | Needs edit, borderline: Namespace typing is grounded, but the wrapper/action and union changes are imprecise. |
| 15 | Fix typo in Nager.Date.UnitTest.csproj | **Misleading regression:** real framework retargeting in two projects is not a demonstrated typo fix. |
| 16 | Fix syntax error in generate.rb | **Still misleading:** only TODO is added inside a comment. |
| 17 | Fix group option | Needs edit: unchanged, generic. |
| 18 | Remove testing flag | **Still misleading, borderline:** removes a use/override, not the flag definition. |
| 19 | Add Goede Vrijdag to PublicHoliday | **Misleading regression:** renames an existing holiday label, not an added holiday. |
| 20 | chore(defaults): update bundle version | Usable: same supported two-file version change. |

Acceptance does not require every detail: cases 2, 11, 12, and 20 could be more
specific but capture a reasonable short main-change description. The scheme
scope in case 10, namespace shorthand in case 14, and usage/declaration distinction
in case 18 are explicitly flagged for reviewer disagreement. Counts must not be
presented as definitive global percentages or cherry-picked improvement.

The separate review completed at **11:24:05 UTC** and checked that **21 input
artifacts** stayed unchanged. Hashes:

- Paired sample:
  `591af183927318e7c1107cfd4ab10bce72d3a1d99ac7695aa91c06db627fd1f2`.
- Paired annotations:
  `addb483b97465318869a34894123d00d1e0e5e075e8cf319ab23bd08ada071d7`.
- Review preservation proof:
  `2ace2f755394abb10f62d0a46cae5911a77cf1c01ebf69677c0002d5891cdadd`.

## Conclusion and remaining product gates

The longer recipe improved aggregate loss/token overlap modestly, but the paired
sample contains both useful gains and new misleading summaries. **Do not promote
it as reliably better or keep increasing epochs automatically.** Address semantic
quality with targeted data/label work and explicit human review rather than
assuming a lower loss solves the observed failures.

An isolated CPU feasibility benchmark can be a separately approved next step
toward an experimental, editable suggestion feature; it would not approve model
quality or distribution. CPU latency/peak process RAM, licensing, and an on-demand
lifecycle remain unmeasured/unresolved. Known source-family, label, privacy and
pretraining-overlap limitations remain. No unattended commit/push behavior or
product integration was added.
