# Experiment 0012: decoding and training-label diagnostics

Date: 2026-10-11. **Inference and assistant reviews completed.** The user asked
to continue improving message quality. This diagnostic performed zero optimizer
updates, did not shrink the training set or rewrite labels, and did not promote
a model. The subsequent [six-epoch comparison](0013-six-epoch-comparison.md) is
recorded separately.

## Observations versus hypotheses

The three-epoch model learned subject-like output, but the existing unblinded
20-case development review found 6 usable, 7 edit-needed, and 7 misleading
subjects. This small assistant sample is not a population accuracy estimate.

- **Candidate selection:** greedy decoding commits to each locally best token.
  A fixed four-beam comparison cheaply tests whether sequence-level search helps
  this checkpoint. Better model likelihood need not mean better factual accuracy.
- **Weak supervision:** original commit subjects can omit the visible change,
  rely on external intent, or call comment-only changes behavioral fixes. Inspect
  training references separately; do not infer this is the only cause from bad
  validation outputs.
- **Undertraining/capacity:** not ruled out. The previous run's learning rate
  approached zero by design, so its epoch-2-to-3 plateau alone cannot prove that
  further training would be useless.

## Fixed decoding protocol

- Reuse `training-0003/checkpoint`, safetensors SHA-256
  `34d66789185036a95c84cb1dd3c169cd2f8b8ba111ad31685d08b099b7738365`.
- All **962 unchanged validation examples**, original complete inputs, pinned
  tokenizer, 512-input/64-output-token budgets; no truncation or prompt edits.
- Compare the saved greedy baseline against **four beams**, greedy token
  expansion (no sampling), `length_penalty=1.0`, `early_stopping=False`, and the
  same maximum 64 new tokens. Native Windows CUDA, float32/eager, batch 8.
- Save four model-ranked candidates, but evaluate **rank 1 only** as the proposed
  policy. Never choose candidates by reference match or assistant annotation.
- Reference presence among four candidates is diagnostic only, not deployable
  accuracy. Do not sweep beam widths, penalties, or checkpoints afterward.
- Reproduce the first 16 saved greedy outputs before comparison. Preserve all
  prior artifacts and write only to new `D:\PushTrackML\runs\decoding-0001`.
- Review the same 20 previously inspected full diffs under the existing rubric;
  retain disagreement-sensitive cases. This is reused development evidence,
  not a blind benchmark. No optimizer updates or new checkpoint are involved.

## Training-only diagnostic protocol

Screen **all 9,758 training rows** with deterministic structural heuristics, then
read four complete diffs/subjects from each of six strata (up to 24 examples).
The complete training set stays unchanged; this is inspection, not a reduced
training run.

Strata, assigned in order: documentation paths (`.md/.markdown/.rst`),
comment-like changed lines, multiple files, additions-only, removals-only, and
single-file replacements. Blank-only/other rows are counted separately. Changed
lines are read inside diff hunks, not inferred from file-header markers. Hash
comments are recognized only for a declared set of scripting/config suffixes;
C preprocessor lines are not treated as comments. These are sampling heuristics,
not language-aware proof of behavior or automatic exclusion rules.

Choose the four lowest SHA-256 ranks of `label-diagnostic-42:` plus commit ID in
each stratum, independent of model output and subject quality. Do not replace
cases after reading. Record label support, specificity and outside-context needs
separately from the original data. Stratified counts cannot estimate global label
accuracy. No labels/holds are edited and validation never becomes training data.

## Observed decoding results

Controller exit **0**; inference ran **13:48:50–13:49:46 UTC**. All 16 greedy
reload predictions exactly matched the preserved baseline. Four-beam generation
on all 962 examples took **54.266 seconds** on CUDA; this is not a CPU benchmark.

| Diagnostic | Greedy | Four-beam rank 1 |
| --- | ---: | ---: |
| Exact reference matches | 0/962 | 0/962 |
| Mean lexical F1 | 0.222125 | 0.219129 |
| EOS emitted | 962/962 | 961/962 |
| Nonempty single line within 72 characters | 961/962 | 948/962 |
| Distinct predictions | 952 | 959 |

Top-1 text changed for **770/962** inputs. Only **one** reference appeared among
any of the four candidates; this is an oracle diagnostic, not rank-1 performance
or semantic correctness. More distinct strings did not mean better summaries.

The same twenty full-diff assistant review yielded:

| Judgment | Greedy | Four-beam rank 1 |
| --- | ---: | ---: |
| Usable | 6 | 4 |
| Needs edit | 7 | 6 |
| Misleading | 7 | 10 |

Seven new judgments are interpretation-sensitive. Examples of regressions:

- Bundler: `use 1.12 instead of 1.12`, although the constraint changes to `~>1`.
- Changelog: invents a `v2.0.0` release from a Semantic Versioning URL in context.
- CLI: `use sys.stderr.write instead of sys.stderr.write`, although error-display
  implementation is being added rather than substituting identical calls.
- Bundle update: replaces the new identifier with itself rather than naming the
  old `20210622` value and new `20210702` value.
- TODO-only change: rank 1 falsely removes `parameter_struct`; rank 2 mentions
  the real TODO addition. A correct lower-ranked candidate is not an automatic,
  reference-free way to select it in production.

Some cases improve from misleading to merely incomplete: a button-comment
correction becomes a vague typo title, a cnki.net pattern is mentioned without
PDF-blacklist detail, and net472 is named while missing net45 removal and the
second project. These subjective boundaries are recorded in `review.json`;
no older judgments were rewritten. **Do not adopt this four-beam policy.**

## Observed training-label diagnostic

All **9,758 rows** were structurally screened, not all semantically reviewed:

| Heuristic stratum | Rows |
| --- | ---: |
| Documentation paths | 965 |
| Comment-like changed lines | 223 |
| Multiple files (after earlier strata) | 1,274 |
| Additions only | 1,614 |
| Removals only | 435 |
| Single-file replacements | 5,238 |
| Other / blank-only | 9 |

Six synthetic parser assertions passed, including distinguishing hunk lines
from file headers and C preprocessor/shebang lines from hash comments. Four
fixed hash-ranked examples per named stratum were read in full: **24 total**.

Assistant label-support judgments: **19 supported, 3 partially supported,
1 unsupported, 1 requiring outside context**. These equal-per-stratum sample
counts are not an estimate of the whole training set's accuracy. Supported
labels can still be generic or contain intent qualifiers not provable locally.

Notable evidence:

- `3dd33bc7c8428e4be8d0f662e63ef42227245948`: original subject **add composer
  install** contradicts the complete diff, which only removes CI sleep/curl
  commands. This is concrete label noise, not proof every model error has this
  cause.
- `c7884d1c5a7b2821e602aa4e76f605a5b304e8a4`: subject says `simtest`, while the
  replaced value is actually `simnet`; the new `testnet` value is correct.
- `ad5feb7e92ebdcd380cbb1429350d5a21f8be826`: **Remove unnecessary bang
  statement** only removes explanatory comments. Wording could mean the prose
  statement but can also suggest removal of executable null-forgiving code.
- `75e440686be42f98282c08f371f3b3e5388791aa`: the new comma-splitting function is
  real, but the subject omits replacement of the old reverse registration.
- `cf434cad2dce7f6da58f974b0254d579b8ecd00d`: **Fix FastQA test** requires test
  context; the visible source change conditionally includes answer spans.

A ReSharper suppression removal also demonstrates why comment syntax alone is
not proof that tooling behavior is unchanged. No heuristic automatically rejects
examples or rewrites targets. **All 9,758 original training rows remain.**

## Evidence and decision

The review/count/preservation proof passed at **14:02:22 UTC**, with **23 protected
input artifacts unchanged**, zero optimizer updates and zero dataset edits. It
checks annotation identities, counts and preservation—not semantic truth by an
independent reviewer. Artifacts under `D:\PushTrackML\runs\decoding-0001`:

- `report.json`, `beam4.json`, `paired-sample.json`, `review.json`.
- `review-verification.json`, `provenance/`.
- `training-label-diagnostic/sample.json`, `review.json`, `provenance/`.

Hashes:

| Artifact | SHA-256 |
| --- | --- |
| Executed decoder diagnostic | `695a39c083cc1691ef6c34ddbe39cd7582ce434635a223e696c4e9d030b75d17` |
| Four-beam outputs | `bb7ecc00d90525d6446d4dd7dd82063f53fd89de4bb1025c59d3844c1bb69f7b` |
| Paired sample | `77d9c2a62fabf1eb8fb04ffe79fe6d29f912a1380c24c02908430e82a79a68b5` |
| Paired review | `597db9e7e1b0e060a2a470fb39dbf443bbca3473a28366a3fe046435a552844d` |
| Training-only sample | `df963f94d63d726a24c9565a8a6fc17fbdae3bfef020b9195bad804b5a66b622` |
| Training-label review | `8fc2c23550835dc6a46050c655b8c8fe570d088043d9e7bd1af2a4cc75540454` |

**33 native-Windows unit/regression tests passed** for the decoding diagnostic
and existing trainers before inference. The unchanged trainer's greedy path was
not replaced. Subsequent six-epoch changes have their own test evidence.

A fresh native-CUDA process additionally verified this diagnostic at **14:35:24
UTC**: rank-1 metric accounting for all 962 examples, and exact reproduction of
**32 candidates on the first eight inputs**, with sequence scores within `1e-6`.
`verification.json` records this separate reload proof; all protected inputs
remained unchanged and verification performed zero optimizer updates.

Beam search did not fix the problem. Weak references are demonstrably present,
but the small diagnostic does not establish their overall prevalence or rule
out undertraining. The next controlled comparison retains the full original set
and tests a bounded longer recipe; label repair is not silently mixed into it.

## Boundaries

Work inline and run data/model work natively on Windows using existing pinned
packages/assets. No new model/data downloads, GitHub checks, test-split reads,
CPU deployment benchmark, Rust integration, compression, commit, or push. Keep
all historical quality flags, original subjects, notices, and provenance intact.
