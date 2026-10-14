# Experiment 0008: full integrity audit and bounded quality review

Date: 2026-10-05. **Technical integrity passed for all 11,000 source examples.
The resulting 9,758 train + 962 validation candidates remain unapproved for
training. Canonical/fork identity checks and broader target-quality review are
not complete. No new training, model download, compression, integration, commit,
or push occurred.**

**Subsequent authorization:** after this audit, the user explicitly approved a
bounded research run on these pending examples despite the disclosed limitations.
[Experiment 0009](0009-corpus-training.md) records that completed run separately;
this audit's historical artifacts and quality-approval flags were not rewritten.

All corpus processing, Git checks, tokenization, API access, and artifact writes
ran natively on Windows under `D:\PushTrackML`. No packages were added. The test
split was not read. Original source exports and historical learning/training
artifacts were preserved.

## Inputs and implementation

Inputs: the immutable `sources-0001/train-pending.jsonl` and
`validation-pending.jsonl` from experiment 0007: 10,000/1,000 records across
185/59 repositories. Their recorded hashes were checked before and after work.

`audit_corpus.py` and `test_audit_corpus.py` add an audit, not a trainer:

- Run full Git object checks in the **244 retained repository caches**. Cached
  Git commands are allowlisted read-only operations; HTTP/HTTPS and other Git
  transports are disabled, including fallback lazy fetches.
- Independently check raw commit identities, exact parent/original-subject
  correspondence, complete Git-tree changed-file coverage, stable patch IDs,
  and source/notice SHA-256 and Git blob identities.
- **Apply every unified diff to exact old file bytes and compare the result
  with exact new file bytes.** Check hunk positions and counts, missing final
  newlines, CRLF, additions/deletions, and multi-file coverage without whitespace
  normalization. This independently verifies actual changes, not just line counts.
- Re-encode every complete diff and subject with the official pinned tokenizer,
  requiring lossless recovery and the recorded **512/64** limits. No truncation
  or model inference is used.
- Check every record's identity, split, shard/row coordinate, and original target
  against the read-only full-corpus SQLite index.
- Check exact/stable-patch duplicates, selected cross-split commit/parent IDs,
  identical whole-file before/after pairs, and path-independent changed-token
  similarity. The near-change check uses five-token shingles, a 40-token minimum,
  and Jaccard >= 0.85. These are defined detectors, not exhaustive proof against
  every form of copied code or pretraining contamination.

## Observed execution and regression proof

**61 Windows regression tests passed**, including nine audit tests and all
52 previous data/source tests. Actual source records also passed a concurrent
cached-Git/tokenizer smoke check.

The first attempt, `audit-0001`, ran 15:58:12-16:07:34 UTC and is preserved.
10,900 rows passed; one 100-row repository worker failed during a cold concurrent
Transformers lazy import (`AddedToken`). It did not report a bad source diff.
The auditor now initializes the official tokenizer/imports on the main thread
before workers construct independent tokenizer instances. No shared tokenizer
backend, dependency replacement, or source-data change was introduced.

The corrected `audit-0002` ran **16:12:23.666039-16:21:07.104750 UTC** and exited
zero. Results:

- **11,000/11,000 technical integrity checks passed; zero integrity errors.**
- Zero exact/stable-patch duplicate groups or configured near-change pairs.
- No detected cross-split commit/parent or whole-file change overlap.
- Zero case-insensitive repository-name overlap. Canonical/fork separation is
  a separate, unfinished check below.

Executed auditor SHA-256:
`6fd4442ce445a139b260debe244bac4e4a739181ff2593cdee05d20719e71a42`.
Audit report SHA-256:
`4214e73f8a9e6a17cb135a45f5f3d2a80993c3acd737739a5b14c051c4c5a5d0`.

## Quality holds and explicit sample review

The audit first withheld **236 train + 34 validation = 270 rows** and wrote
new screened-pending exports; it did not delete or rewrite original records.
All eight earlier sample holds were applied. Reasons overlap, so reason counts
must not be added as if they were independent rows:

- 196 email-like strings in model-input context, including potentially benign
  public contacts or fixtures; this is a conservative privacy hold.
- 56 generated-source header matches in old/new file snapshots.
- 11 non-diff attribution targets and two generic documentation targets.
- The eight previously recorded subjective quality holds, some overlapping
  the automatic rules.

A second deterministic sample selected **one row from each of 12 repositories
per split**, using SHA-256 ordering with `final-quality-42`. The coding assistant
read all **24** diffs and original subjects:

- **18 diff-supported** subjects.
- **6 held**: three low-specificity, one coverage, one external branch-context,
  and one incomplete-English subject.

This is repository-stratified sampling, **not** a uniform row-quality estimate
or independent human annotation. Across both samples, **40 distinct records**
were reviewed by the coding assistant: 26 diff-supported and 14 held. Most
remaining labels are still unreviewed original-message weak supervision.
No subjects were silently rewritten or polished.

A supplementary conservative literal-assignment screen covers quoted JSON keys
and short nonempty password/key/secret strings that the earlier heuristic could
miss. It withheld **four further rows (three train, one validation)** without
printing values or testing credentials. They may be benign fixtures; **they are
not claimed to be confirmed secrets**. Three synthetic guard assertions passed.
The finalizer and its decisions are saved in Windows provenance.

### Current candidate count, not training approval

| Stage | Train | Validation |
| --- | ---: | ---: |
| Source-checked | 10,000 | 1,000 |
| First audit holds applied | 9,764 | 966 |
| Six additional sample holds applied | 9,761 | 963 |
| Four additional assignment holds applied | **9,758** | **962** |

**280 total rows are held; 10,720 unique candidates remain.** No replenishment
was performed just to restore a round target count. Every new export still has
`training_approved: false` and a pending status; it is not a fully reviewed set.

## Canonical/fork identity gate: blocked

The bounded public GitHub metadata pass checked **51 of 244 repositories**.
It stopped with **five unauthenticated requests remaining**, respecting the
existing reserve. All 51 responses were successful, and no checked repository
was marked as a fork. This does **not** clear the other **193** identities or
establish full split separation.

`families.json` preserves canonical repository IDs/names, fork-family IDs, raw
response hashes, and the stop reason. API bodies are retained locally for
provenance. No credentials were requested in chat, used, or installed. The
Windows GitHub CLI was not present. Completion needs an approved later bounded
pass after reset, or separately approved safe local, least-privilege public
metadata authentication; do not route around the quota or downgrade the gate.

Even complete current GitHub metadata would not prove absence of detached
forks, copied repositories, or model-pretraining overlap. Known notice-name and
secret-pattern checks likewise do not certify exhaustive legal/privacy clearance.

## Artifacts and final preservation proof

```text
D:\PushTrackML\data\corpus-0001\
    audit-controller-0001.json       # stopped first audit; retained
    audit-0001\
    audit-controller-0002.json       # corrected attempt; exit zero
    audit-0002\
        report.json
        integrity.jsonl
        content-overlap.json
        families.json
        repository-metadata\
        holds.jsonl
        train-screened-pending.jsonl
        validation-screened-pending.jsonl
        final-quality-sample.json
        final-quality-review.json
        provenance\
        post-review-pending\
            train.jsonl
            validation.jsonl
            additional-holds.json
            manifest.json
            verification.json
```

Final export SHA-256:

- Train (31,577,764 bytes):
  `5dd4d286b73bea89456bdb2cb3c5cb23a3757ad38a6baaa37099fe5f0a4d4269`.
- Validation (3,138,527 bytes):
  `76b9d83b60741738c29dc53f8629ec4c0e08434427595a5191682f19f42ba2ee`.
- Final manifest:
  `b5b8bd9ed83c1fb6629d6626cb63f51a69904c8669c6763fd8a0d5001a046e21`.

The closing proof verified counts/hashes, uniqueness, exclusion of every known
review hold, zero repository-name overlap, and unchanged retained-record fields
except review status. Original subjects/diffs were not rewritten. It also
reconfirmed hashes of the old 11/5 learning files, training report, and
safetensors checkpoint. This audit proves data engineering checks, **not model
quality, full semantic label correctness, production readiness, or permission
to launch another training run**.
