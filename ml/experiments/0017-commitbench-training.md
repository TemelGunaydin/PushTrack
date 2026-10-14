# Experiment 0017: fixed CommitBench three-epoch comparison

Date: **2026-10-12**. **Completed at the declared stop: 10,000 original-label
training examples, three complete epochs, independent accounting/reload proof
and the same twenty-case development review. No demonstrated improvement or
product promotion.**

## Authorization and immutable data boundary

The user approved starting the proposed comparison and asked whether increasing
epochs improves training. That question did **not** authorize automatic extension.
This is one bounded **noncommercial** research run, not semantic certification.
All real tests, tokenization, training and model verification ran on native
Windows at `D:\PushTrackML`; the Mac edited/control-led and read returned evidence.
No subagents, new dataset/model/package acquisition or authentication work.

Training uses **all 10,000 additional CommitBench expansion records**, not only
the forty reviewed targets, the earlier 117-row pilot, the unverified candidate
pool, or a merge with the historical 9,758 rows. Complete original Git diffs and
original subjects are unchanged. The prior forty-target review found 29 supported
and 11 partial labels; **9,960 remain semantically unreviewed**. All four new and
nine historical target proposals remain unapplied.

- Train: `data\commitbench-0001\sources-0002\train-pending.jsonl`.
  SHA-256 `2840e70b84b9d8d3e26559724b83076e5c55e75701cdd9148cb1a9f103b151b2`.
- Immutable manifest:
  `613b468481b01e2044390e37dce89a93aa5ae86f1c45ebe168fbef517750f295`.
- Same **962 development-validation rows**:
  `data\corpus-0001\audit-0002\post-review-pending\validation.jsonl`,
  `76b9d83b60741738c29dc53f8629ec4c0e08434427595a5191682f19f42ba2ee`.

The alternate loader explicitly pins these data/evidence hashes, exact counts,
review/provenance/integrity/license flags, cross-split identities/stable patches
and case-folded repository names. Official tokenization rechecks every row with
**512 input / 64 target** limits and no truncation. Historical Chronicle defaults
and gates remain intact; no arbitrary-path/unpinned profile was added. CommitBench
accepts only an explicitly requested three-epoch recipe.

CommitBench remains **CC BY-NC 4.0**, separate from the original source MIT notices.
Incomplete canonical/fork coverage, privacy, near-copy/pretraining overlap and
CodeT5 distribution wording remain unresolved. The independent train CSV is
commit-random, not the publisher's repository-separated benchmark. Source
integrity is not target correctness. Existing `training_approved: false` and
manifest `research_run_authorized: false` remain unchanged; scoped user permission
is separate in `runs\training-preflight-0005.json` and the run report. Test data
was neither acquired nor read. Validation is evaluation-only, never backward,
optimizer updates or training-target correction selection.

## Fixed recipe and execution

- Original verified CodeT5-small weights, not a prior adapted checkpoint.
- **Three complete epochs**, shuffle seeds **42–44**, batch **8**.
- **1,250 updates per epoch / 3,750 total / 30,000 exposures**. Every identity
  exactly three times; no dropped rows or diagnostic-only training subset.
- Maximum LR **5e-5**, AdamW decay .01, betas (.9, .999), epsilon 1e-8,
  gradient clip 1; **188 warmup updates**, global decay across the full recipe.
- Deterministic float32/eager CUDA, seed 42, four CPU threads. No AMP, LoRA,
  quantization, CPU fallback or optimizer-state continuation.
- Save all three safetensors checkpoints. **Final epoch 3 selected before launch**;
  no post-hoc replacement with the lower-loss epoch 2.
- Greedy, target-free decoding, one beam and at most 64 new tokens. Full train/
  validation losses, all 962 validation generations and fixed 64 training cases.

**46 native trainer/decoder tests passed** with the final executed source.
Preflight loaded all 10,000/962 rows and verified existing protected inputs;
RTX 4070 observed approximately 11.65 GB free GPU memory and 165.49 GB free disk.
Retained SSH controlled Windows PID **4316**, controller exit **0**.

Trainer: **11:01:43.985929–11:16:13.290116 UTC**, approximately **14m29s** including
baseline/evaluations and saving; optimizer loops totaled **448.988 seconds**.
No worker remained active at the final read-only check. Existing CUDA allocator
statistics are not CPU process-RAM or deployment-latency measurements.

Recorded invocation (already completed; **do not overwrite or rerun**):

```powershell
& 'D:\PushTrackML\.venv-train\Scripts\python.exe' .\train_corpus.py `
    --workspace 'D:\PushTrackML' --output 'D:\PushTrackML\runs\training-0005' `
    --epochs 3 --data-version commitbench-source-0002
```

## Observed measurements

| Stage | Train loss | Validation loss | Validation lexical F1 | Exact subjects |
| --- | ---: | ---: | ---: | ---: |
| Original weights | 9.058728 | 8.699134 | .012393 | 0/962 |
| Epoch 1 | 2.978001 | 3.307108 | .183757 | 0/962 |
| Epoch 2 | 2.717738 | 3.227649 | .202513 | 0/962 |
| **Preselected final epoch 3** | **2.625016** | **3.237322** | **.201382** | **0/962** |
| Historical Chronicle three-epoch final, same validation | 2.419144 | 3.126153 | .222125 | 0/962 |

Training losses across different corpora are not directly comparable. The new
final validation loss/lexical overlap are worse than the historical three-epoch
recipe. This is **not** an isolated dataset-quality effect: row counts, updates
(3,750 versus 3,660), warmup (188 versus 183), source composition and references
differ. Final generations emitted EOS and single-line subjects of at most 72
characters for all 962 cases, with 954 unique predictions. Format is not semantic
correctness, and lexical overlap/exact wording is not accuracy.

## Same twenty development cases

Every complete diff was read; cases are the original SHA-256-ranked
`result-sample-42:` selection, with no substitutions or outcome-based selection.
These are **repeated, unblinded assistant judgments**, not independent human gold,
a blind final test or a population success rate. References have their own
support limitations; twelve new judgments are interpretation-sensitive.

| Recipe | Usable | Needs editing | Misleading |
| --- | ---: | ---: | ---: |
| Historical Chronicle three epochs | 6 | 7 | 7 |
| CommitBench final three epochs | **5** | **10** | **5** |

Some activation/comment descriptions improve, while more outputs remain vague.
The false methods-for-properties claim persists; Bundler is falsely added when
only its constraint changes; an existing CliError is described as a new class;
a test-conditional cacheability override is mistaken for cached-data deletion;
a Dutch holiday-label correction is still described as adding the holiday.
Borderline comment/namespace/mapping/empty-input shorthand is recorded explicitly,
not hidden as certainty. The mixed counts **do not establish superiority**.
Neither checkpoint is promoted.

## Epoch question and stop decision

More epochs can improve fitting training data without improving unseen diffs.
Here training loss kept falling but validation loss rose **3.227649 → 3.237322**
from epoch 2 to 3; lexical F1 also slipped. This alone is not a universal claim
about longer training or all datasets. It does reinforce why automatically
continuing is unsafe. The earlier six-epoch Chronicle recipe similarly worsened
validation after epoch 3 (**3.118129 → 3.189596**) despite lower train loss.

The predeclared final-epoch comparison is preserved, not retroactively changed
into a validation-selected experiment. No further epochs, label application,
compression, CPU/RAM profiling, Rust integration, commit or push followed.
Any next experiment needs a separate approved recipe and preserved version.

## Independent proof and retained artifacts

Fresh native proof verified every epoch's identity order, all **3,750** step/LR/
finite-gradient/training-mode entries, **10,000 identities × three exposures**,
every loss-batch accounting and generated identity/target alignment. The complete
original validation baseline reproduced exactly. All three checkpoint hashes
passed; a fresh final-model load reproduced **16 predictions and two batch
losses within 1e-6**. Intermediate checkpoints are hashed, not all independently
re-evaluated. Original weights differed from the trained embedding probe.

Proof preserved **87 protected artifacts**; the review/preservation check
preserved **97**, including new run measurements/checkpoints. Review verification
checks identities/counts/hashes, **not independent semantic truth**. Zero optimizer
updates occurred during proof/review. A final read-only display helper initially
requested a nonexistent `total_wall_seconds` field; computing duration from the
recorded timestamps corrected it. No training/proof writer was restarted or
artifact overwritten because of that display error.

Artifacts: `D:\PushTrackML\runs\training-0005\` with `report.json`, `steps.jsonl`,
`baseline.json`, `epoch-1.json`, `epoch-2.json`, `final.json`, `verification.json`,
`checkpoint-epoch-1\`, `checkpoint-epoch-2\`, `checkpoint\`, executed `provenance\`
and `quality-comparison-0001\{sample,review,verification}.json`.
Controller: `runs\training-controller-0005.json`; training and 46-test stdout/
stderr logs are retained separately. Data/model weights and annotation-bearing
one-off helpers stay outside Git.

| Artifact | SHA-256 |
| --- | --- |
| Executed trainer | `503174ce6387099db011717b859d066179280e885122339662a3def6a6cbfb34` |
| Alternate-loader tests | `980153e4f92e701c6c53792fc5cdada67f8d7e6398870288eaa0f04585c2fbaf` |
| Epoch 1 weights | `d8f00cfabd0a19a62575e399b3ab999f9214e224e3af2196d25e1e133eaf1d90` |
| Epoch 2 weights | `a1436af60907bea47bb81ef9044dbd0aca9c5f065a993c07bd66fd5b7a57c062` |
| Final epoch 3 weights | `54224dce65c5e7874bb3c06389582f6eb100772b45cd02884c2c188e0c7f37fb` |
| Report | `710c4db673618614749c5f6b1c8a39ed115d1d5effefac8931c675e158d0c38b` |
| Steps | `b8fb4378cdf4898c8dd72ce679eeae28a972fc580314ce3310502e973546f4e1` |
| Fresh proof | `aa0f64ba579da07036aa5b130cf0fb9c140edcb41d6989054c5642995c6901cd` |
| Fixed paired sample | `3506e344fb69497d1ce05a36352741d1a431cd0f5043db4677b16d312689f435` |
| Separate review | `782bcd2d08d9df8bee682c9742593013319db61b9691a6539558324a5a936755` |
| Review preservation proof | `e4e7ac027466a4bdda73e45df836e26e02b945b6392219e799ee6e307f5b99fe` |
