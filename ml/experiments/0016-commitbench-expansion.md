# Experiment 0016: bounded CommitBench source expansion

Date: **2026-10-11**. **Completed: 10,000 additional source-checked pending
records, fresh mechanical proof and the declared forty-target review. No model
training.**
This report describes the completed source-preparation stage, before the later
separately authorized [training comparison](0017-commitbench-training.md).
The user approved expanding the already acquired CommitBench candidate pool,
not model training at this stage. All real processing is native Windows under
`D:\PushTrackML`, using the existing data environment and tokenizer.

## Fixed contract

- Target: at most **10,000 additional** complete training records, not guaranteed
  retention and not a 40-record training exercise.
- At most **192 candidates attempted / 100 reconstructed per repository**,
  two workers and a **two-hour network/reconstruction deadline**. Offline
  audits can finish after that deadline; no new source fetches after it.
- Stop after an **8 GB local-Git storage threshold** checked between batches;
  **256 MB per repository** and **20 GB disk reserve**. Storage thresholds are
  not exact transfer-byte caps, and a completed batch can cross the global
  threshold.
- No corpus/model reacquisition, new packages, authentication setup, GitHub
  metadata sweep, rate-limit workaround, automatic retry or restart.
- **CC BY-NC 4.0** applies to CommitBench; original source MIT notices remain
  separately verified/preserved. This is noncommercial research, not commercial
  or model-distribution clearance.

## Reuse and selection

`ml/expand_commitbench.py` reuses the existing `GitSource`, original commit/file/
notice gates, `materialize`, `audit_repo`, official tokenizer, overlap checks
and CommitBench provenance adapter. Original shared source/audit modules were
not changed or relaxed for this run.

Candidate CSV/SQLite remain immutable. Restrict names to the existing Chronicle
training universe; reserve validation names/known aliases. Exclude every earlier
191-candidate pilot identity, including rejected/uncertain cases, and earlier
source/pilot/hold identities. Deterministic repository order hashes
`commitbench-expansion-repositories-42:` plus repository name; candidate order
uses the pinned SQLite priority, without outcome-based replacements.

The predeclared plan contains **52,624 candidates / 1,002 repositories** after
identity exclusions and the per-repository attempt cap. The target and deadline
stop collection before all selected candidates need be attempted.

Prior bare Git object caches are copied into **new owned repositories**, never
mutated. Earlier refs/config are not copied. Local object inspection disables
lazy fetching; only missing blobs are explicitly acquired. SHA/type/coverage
checks guard cache reads, and every seed cache's file tree is hashed before and
after reuse. No checkout or source-code execution occurs.

All two-worker batch writers finish before read-only audits begin, avoiding
concurrent reads of shared content-addressed snapshot/notice files. Every
reconstructed example must pass full-file and hunk application to exact old/new
bytes, parent/subject identity, original tree/notice coverage, stable patch and
lossless **512 input / 64 target** checks. A repository with integrity errors
is held, not admitted by dropping failed files.

Old/new commit, stable-patch, changed-text and file-change overlap are screened,
along with selected validation commit/parent identity and configured
near-validation changed-token overlap. This is not exhaustive fork/copy or
pretraining-contamination clearance. Source/privacy/English heuristics remain
imperfect; inspection flags do not automatically rewrite or approve targets.

## Version and review boundary

Output is a **separate pending version** at:
`D:\PushTrackML\data\commitbench-0001\sources-0002\`.

Every original complete diff, subject, identity, dataset coordinate and applicable
notice remains traceable. No merged old/new training export is created. The
original 9,758/962 exports, previous 117-row CommitBench pilot, models/reviews,
quality holds and nine unapplied target proposals stay unchanged. Pending
records/manifest retain `training_approved: false`; no optimizer updates or
training authorization are inferred from acquisition approval.

Before collection, declared a **40-row training-only** review: first SHA-256
ranks of `commitbench-expansion-quality-42:` plus identity over all new survivors,
no predictions, substitutions or validation-target selection. The forty are a
quality diagnostic, not the future training size. **9,960 targets remain
semantically unreviewed** after this sample; assistant review is not gold
human annotation or model accuracy.

## Collection outcome

The retained-SSH controller completed with **exit 0**. Collector runtime:
**19:11:43.749796–20:11:37.535961 UTC**, approximately 59 minutes 54 seconds.
It stopped at the 10,000-record target, not at the two-hour deadline; no extension
or retry was launched.

- **18,385 candidates attempted / 370 repositories checked**.
- **10,092 complete source reconstructions passed the per-batch integrity audits**.
- Six stable-patch and 41 changed-text overlaps held; 45 additional valid rows
  were not retained after reaching the global target.
- **10,000 additional pending records / 344 repositories**, all original subjects.
- **34,239 selected candidates remained unattempted** at the declared target stop.
- Git storage: **179,092,719 bytes**. Nineteen old cache trees were reused and
  preserved; 57 already-present local blobs did not require a blob fetch.

Full attempted-candidate accounting:

| Outcome | Records |
| --- | ---: |
| Pending survivors | 10,000 |
| Missing recognized root MIT notice | 2,690 |
| Original commit encoding/subject policy | 2,158 |
| Unmaterialized at per-repository cap | 887 |
| Original/published subject mismatch | 817 |
| Non-standard MIT notice | 797 |
| Repository unavailable/unsupported | 566 |
| Possible sensitive assignment in source | 101 |
| Conflicting license notice | 100 |
| License path depth | 86 |
| Git output budget | 82 |
| Unretained at global target | 45 |
| Duplicate changed text | 41 |
| Conflicting source notice | 8 |
| Duplicate stable patch | 6 |
| Generated content | 1 |
| **Total attempted** | **18,385** |

The 566 unavailable/unsupported records are from `atk4/atk4`, `jsdom/jsdom` and
`lsegal/yard`. The bounded runner did not establish a more specific cause; no
alternate endpoint, automatic retry, or gate relaxation was attempted. Encoding/
subject rejections include policy failures, not necessarily corrupt text. Caps
are unprocessed/unretained budget outcomes, not semantic label verdicts. Possible
sensitive assignments are not confirmed secrets.

Composition: **731 multi-file records**, at most three changed files per retained
record; input lengths **88–510 tokens**, target lengths at most **25 tokens**.
This is not evidence that the model can summarize such commits correctly.
There are **199 inspection-flagged records**: 157 email-like contexts, 38 generated-
header flags and seven non-diff attribution targets, with overlapping reasons.
These leads were not silently removed, sanitized or treated as semantic verdicts.
Only **2/344 repository names** match the earlier family-metadata cache. No new
canonical/fork sweep was performed; the much larger unresolved-name coverage,
near-copy and pretraining-overlap limitations remain explicit.

## Completed target review and unapplied proposals

All forty declared complete training diffs were read. Separate assistant notes:
**29 supported / 11 partially supported**, with **17 interpretation-sensitive**
judgments. Supported means the main visible action is grounded, not that every
adjective, runtime result or motivation has been independently proved. Partial
cases include incomplete conditions, outside-context motivations, ambiguous
locations/terminology and one concrete reference-count mismatch. No model
prediction or validation target was used to choose or replace cases.

Four traceable, officially tokenized suggestions are recorded separately:

| Commit prefix | Proposal kind | Proposed target |
| --- | --- | --- |
| `8fa50bdce9d1` | Incomplete-condition clarification | Reject STS requests when the signer is missing |
| `d381ee92fd56` | Location clarification | Move collection index deletion out of _removeReference |
| `02b2c2a95b6c` | Terminology clarification | Log an error when carb ratio data is missing |
| `3c7d92e4cc1d` | Factual count correction | Correct rollBack method casing in ORM transaction calls |

The final case says two references, but the full diff changes **three** call
sites across two files. The other suggestions avoid an incomplete missing-signer
condition, questionable `model.remove` naming, or carb-sensitivity versus the
actual carb-ratio input. They are proposals, **not four automatically bad labels**
and not applied changes. The original nine Chronicle proposals also remain
unapplied. All 10,000 new subjects and quality flags are preserved.

The sample does not prove global label quality, superiority over Chronicle,
or model accuracy. It uses a different selection method from earlier diagnostics;
29/40 must not be advertised as a population success rate or compared as model
accuracy to the previous 15/20 target review. Most new references remain
unreviewed, and no trained model has yet used this version.

## Verification and preserved artifacts

- Native preflight passed: old candidate/export hashes matched, no worker
  overlap, approximately **166.17 GB** free disk observed before launch.
- **36 native expansion/preparation/source/audit tests passed** before launch,
  including cache preservation, missing-blob fetches, strict identities,
  deterministic caps/sampling, integrity holds and no automatic label approval.
- Fresh proof at **20:13:08 UTC** verified all 52,624 planned records against the
  deterministic SQLite selection and all 18,385 attempted identities/outcomes.
  SQLite quick-check was `ok`.
- All **10,000 pending records freshly retokenized losslessly**; all **10,750 file
  patches re-applied to exact snapshots**, notices rechecked, configured old/new
  overlap proof passed with zero near-validation hits. These checks are not
  exhaustive copy/fork or pretraining clearance.
- Thirty-two declared identity-ranked examples also received a fresh cached-Git
  parent/tree/notice audit. This does not replace the complete earlier audits.
- All **74 protected artifact hashes / 19 reused cache trees** preserved.
- Separate review proof at **20:17:59 UTC** checked the forty identities/counts,
  four proposed token budgets and **85 protected artifacts**, including the new
  frozen collection/proof outputs. Mechanical proof is not independent semantic
  annotation.
- **Zero dataset target changes, zero automatic semantic exclusions, zero
  optimizer updates**, no test/new validation acquisition.

The user briefly stopped work after the review had completed, cancelling only
unfinished documentation/reporting. After the subsequent continue request, a
read-only native check confirmed all recorded output hashes/counts and earlier
protected artifacts, and **no active PushTrackML Python worker**. No collector,
output-creating verifier, review writer or training job was rerun.

Artifacts in `sources-0002/`:

- `selection.json`, `protected-inputs.json`, `repositories.jsonl`, `outcomes.json`.
- `train-pending.jsonl`, `manifest.json`, `report.json`.
- `verification.json`, `fresh-git-audit.json`, `near-validation-overlap.json`.
- `quality-sample.json`, `quality-review.json`, `quality-review-verification.json`.
- Original Git objects, snapshots/notices and executed `provenance/`.

Controller/logs: `D:\PushTrackML\runs\commitbench-expansion-controller-0001.json`
and `commitbench-expansion-0001.stdout.log` / `.stderr.log`. The immutable
collector manifest/report record the pre-review stage; the later review and its
proof are separate completion evidence, not in-place changes to that version.

| Artifact | SHA-256 |
| --- | --- |
| Pending 10,000-row export | `2840e70b84b9d8d3e26559724b83076e5c55e75701cdd9148cb1a9f103b151b2` |
| Pending manifest | `613b468481b01e2044390e37dce89a93aa5ae86f1c45ebe168fbef517750f295` |
| Forty-target sample | `49a04cb9b68429eb910bd32cac1496530a3db95fe31cc87e5fac081a7daa7f83` |
| Separate target review | `6fea3e218762220b414d7e84eaf413a364b4d8211a6d401a8fc9c3998e0e99e1` |
| Fresh verification | `c56e8a217932e67474cc5a7dffc39883bdf3eda71b6340f90ac08a9ec38cc6e7` |
| Review verification | `8db07127a9d96ccea1231e3e6fc0f4097f8830d9205f2e6f0eb83a2241723059` |
| Executed expansion adapter | `ec49c0a808038a19f5e7b380a83253b6787819ebda702e6a1e4e0d41ef95b1cf` |

## Next decision

A separate, source-verified **10,000-row CommitBench pending version** now exists;
the historical 9,758/962 set and 117-row CommitBench pilot remain separate and
unchanged. Do not confuse the 40 diagnostic examples with a training limit, or
merge all 68,396 unverified candidates into training to inflate the count.

Training needs a separately approved fixed recipe, explicit research
acknowledgment of the weak/unreviewed labels and unresolved coverage/terms, and
an exact version/hash-aware loader. A useful next comparison is three epochs
from the original pretrained weights using **all 10,000 new pending records**,
with unchanged 962-row development validation, no test access and final-epoch
selection declared before launch. This is only a proposed research comparison;
the different row count also changes update count/LR schedule, so it is not an
isolated proof that one dataset is universally better.

Keep all correction proposals unapplied for that pure original-label comparison,
and record any later target intervention in a separate version. Preserve false
quality-approval flags; user run authorization belongs in separate run evidence.
No further acquisition, training, Rust changes, CPU/RAM profiling, compression,
integration, commit or push occurred during finalization.
