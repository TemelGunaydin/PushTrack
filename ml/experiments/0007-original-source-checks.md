# Experiment 0007: batched original-source checks (completed)

Date: 2026-10-05. This continues authorized **data preparation**, not training.
The full-corpus candidate pool from experiment 0006 contains **743,787 train +
133,228 validation candidates**. This pass reached **10,000 + 1,000** complete,
source-checked examples. These are not automatically quality-approved labels.
No new model or training run was started. The subsequent integrity/quality audit
and its remaining blockers are recorded in [experiment 0008](0008-corpus-audit.md).

## Why Git, rather than per-commit REST calls

The previous small collectors stopped at the unauthenticated GitHub API reserve.
`verify_corpus_sources.py` uses ordinary public Git transport: bare repositories,
exact object IDs, depth-two commit batches, and explicit batches of required
blobs. There is no working-tree checkout, source execution, submodule recursion,
LFS hydration, credential prompt, alternate endpoint, or quota workaround.
HTTP access/rate-limit errors stop the pass; failed requests are not retried.
Unavailable repositories are recorded rather than replaced with invented data.

Git is the installed **2.47.1.windows.2**. All Git objects, temporary files,
source snapshots, SQLite queries, tokenization, and exports stay under
`D:\PushTrackML`. The separate `.venv-data` environment is reused unchanged.
Two repositories ran concurrently; a Mac SSH control process kept the native
Windows job attached. That recorded source job has now exited successfully.

## Implemented checks

- Select repositories in deterministic SHA-256 order (seed 42), then candidates
  by the existing seeded priority. Require at least eight index candidates per
  repository; inspect up to 64 validation or 192 train candidates per repository.
  This favors sufficiently represented repositories and is not unbiased sampling.
- Validation goes first. Retain at most 20 validation or 100 train examples per
  repository. A larger source pass does not modify original split assignments.
- Require the exact original subject and a single parent. Use original Git trees
  to enumerate **all** changed files, not CommitChronicle's processed subset.
- Reject unsupported paths/modes, symlinks, submodules, known binary/generated
  paths, excessive file counts, and unsupported/oversized output. Generate a
  complete native Git diff with no external diff or textconv and no rename
  compaction. Existing hunk/file/addition/deletion checks are reused.
- Preserve root and recognized ancestor-directory MIT notices at both commit
  and parent. Root notices are required; recognized conflicting nested notices
  reject the commit. Standard-MIT text screening is not comprehensive legal
  clearance; uncommon notice names and third-party provenance remain limitations.
- Preserve and screen both old and new changed-file blobs (up to 200 KB each).
  Check Git blob identities independently and reuse existing secret/SPDX/conflicting
  notice checks. No silent file or hunk removal and no target rewriting.
- Count the complete diff with the official pinned CodeT5 tokenizer. Enforce
  lossless encoding and **512 input / 64 target** limits without truncation.
  Tokenizer warnings about oversize inputs describe examples that are rejected;
  no model is loaded and these inputs are not sent into training.
- Deduplicate whitespace-insensitive stable Git patch IDs. Reject a training
  repository's selected rows if their commit/parent IDs intersect accepted
  validation objects. This is **not** an exhaustive fork-family, copied-code,
  near-duplicate, or pretraining-contamination audit.

Two-hour time budget; 8 GB Git-storage stopping threshold across the pass;
256 MB repository threshold checked after fetch batches; 20 GB disk reserve.
Storage thresholds are not exact network-byte caps and may be crossed by the
last batch. Counts remain meaningful if the bounded pass stops short.

Outputs deliberately use `review_status: source_checked_pending_quality_review`
and `training_approved: false`. Original subjects are weak supervision, not
independently audited labels. A completed source pass still needs target-quality
and stronger repository/fork-family review before an approved larger experiment.
The existing tiny trainer is hash-locked to its old 11/5 set and does not consume
these pending exports.

## Evidence so far

- **52 Windows data/source tests passed**, including all prior data/tokenizer
  tests and seven focused source tests. Synthetic Git tests never access the
  network. Checks include original subject/parent, full file enumeration,
  unsupported modes, nested notices, output limits, option-injection rejection,
  and deadline stop behavior.
- Live end-to-end checks retained two previously verified commits from
  `amphp/amp` and `archiveteam/archivebot`, including one multi-file example.
  Parent IDs and stable patch IDs match the independent earlier GitHub diffs.
  Native Git's function-context text on the `@@` headers differs, so raw diff
  hashes differ; changed/context lines themselves are unchanged. Inputs contain
  172 and 459 tokens. Old/new snapshots and notices were preserved.
- The smoke artifacts and executed code snapshot are under
  `data/corpus-0001/source-smoke-0001/`; the initial transport-only proof is in
  `source-probe/`. They are not silently merged into the larger pending set.
- The bounded large pass ran **12:57:22.700622-13:47:43.124757 UTC**, about
  50m 20s, and exited zero with `targets_reached`. It retained **10,000 train +
  1,000 validation** examples across **185 + 59 repositories**, after checking
  254 repositories. Stored Git data: **292,870,484 bytes** (not total network
  transfer or total snapshot storage).
- Train source export SHA-256:
  `201004bf2ee29e1370bd86527b10d616d63ea62d84a9aed323b51b5c3535a961`
  (32,310,058 bytes).
- Validation source export SHA-256:
  `98d735daa35aeb8e73a216be78b2fb85c1f9680f9e0ba4450b9496ba9851a869`
  (3,267,103 bytes).
- Executed bulk verifier SHA-256:
  `0c00b16cf5fd8e4a1077ee0bd2e10f43f4fcc191723d46045273256277826fa5`.
- The completed corpus audit reconfirmed unchanged old learning-set, training
  report, and checkpoint hashes; D: had 170,604,097,536 free bytes before this pass.

## Initial target-quality audit

A deterministic sample of eight rows per split was captured when the exports
contained 1,000 validation and 950 train rows. The coding assistant reviewed
all 16 diffs, retaining the original subjects unchanged in the evidence:

- **8 diff-supported subjects**.
- **8 held**: two language-quality problems, three low-specificity subjects,
  one language/coverage issue, one non-diff thank-you attribution, and one
  unclear or possibly opposite description of the change.

This is a small **prefix sample**, not an unbiased final-dataset quality estimate,
independent human annotation, or approval of 11,000 labels. Held rows have not
been silently deleted from the active source exports. The review is recorded
separately in `quality-sample-0001.json` and `quality-review-0001.json`.
Quality exclusions must be applied explicitly before producing a training set.

The sample also demonstrates that omitting dedicated author metadata columns
does not remove public author contacts embedded in original source context.
Original diffs/notices can contain such information; do not claim these artifacts
are comprehensively anonymized or free of all sensitive information. Known-secret
screens, source verification, and target-quality review are distinct checks.

## Artifacts and reproduction

```powershell
# Run from the copied Windows experiment directory; use a NEW output only.
# The recorded pass is complete; do not rerun it to perform the later audit.
& 'D:\PushTrackML\.venv-data\Scripts\python.exe' -m unittest -v `
    test_verify_corpus_sources test_prepare_corpus test_download_corpus `
    test_prepare_pilot test_compare_tokenizers test_continue_pilot
& 'D:\PushTrackML\.venv-data\Scripts\python.exe' .\verify_corpus_sources.py `
    --workspace 'D:\PushTrackML' `
    --output 'D:\PushTrackML\data\corpus-0001\sources-new'
```

The completed attempt used `sources-0001/`, with `report.json`,
`repositories.jsonl`, `validation-pending.jsonl`, `train-pending.jsonl`,
`licenses/`, `source-files/`, `repos/`, and `provenance/`.
`source-controller-0001.json` and `source-0001.stdout.log` / `.stderr.log`
are alongside that directory. The controller records the owned Windows PID and
exit status. No service, scheduled task, automatic restart, training, model
compression, Rust behavior change, commit, or push is part of this work.
