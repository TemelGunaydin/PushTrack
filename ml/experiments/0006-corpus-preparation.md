# Experiment 0006: corpus acquisition and candidate filtering (completed)

Date: 2026-10-05. The user authorized downloading the necessary CommitChronicle
corpus rather than restricting selection to two pilot shards. **This step does
not authorize a new training run. Acquisition and candidate filtering completed.
No large training-ready set is claimed by this note.**

## Scope and pinned inventory

Dataset: `JetBrains-Research/commit-chronicle`, revision
`5fd076e67b812a9f3d1999e5e40f71715f84bb51`.

| Split | Shards in download scope | Rows in the pinned inventory |
| --- | ---: | ---: |
| Train | 61 | 7,659,458 |
| Validation | 12 | 1,554,042 |
| Test | **0** | 1,486,267, deliberately not read/downloaded |

The authorized train/validation pool is **9,213,500 records**, stored in
**12,205,933,927 bytes** of Parquet shards. The approximately 10.7M figure includes
the held-out test split; it is not a count of automatically suitable training
pairs. Existing verified pilot shards are hard-linked locally, saving another
332,530,557-byte transfer. All new downloads, hashing, Parquet reads, tokenizer
work, SQLite data, and exports run natively under **`D:\PushTrackML`**.

The Windows preflight observed 185,855,115,264 free bytes on D: and an installed
Git CLI. This is ample for these shards and filtered exports; the downloader
also requires a 20 GB reserve. No complete decoded corpus is loaded into RAM.

## Download behavior

`download_corpus.py` validates the pinned manifest, split shard sequences, LFS
SHA-256 hashes, and byte sizes. Three downloads can run concurrently. A failed
request stops new work; there are no automatic network retries or quota
workarounds. Every completed shard is hashed and its Parquet row count checked.
The job does not fetch test data or execute dataset repository scripts.

`data/corpus-0001/hub-tree.json` is the saved Hub tree response. Immutable
per-attempt download reports and the executed downloader snapshot go in
`data/corpus-0001/downloads/`. A rerun reuses valid existing shard bytes rather
than silently replacing corrupt artifacts.

An initial `Start-Process` attempt did not survive the Windows SSH session's
termination and acquired no shards. The active attempt keeps its SSH session
open using a detached Mac **control** process; processing/downloads themselves
remain on Windows. Keep both computers awake and Tailscale connected while these
controllers run. No service, scheduled task, or startup entry was installed.

### Recorded acquisition result

The successful Windows attempt ran **11:27:36.417046-11:47:34.697504 UTC**.
All **73 shards** passed SHA-256 checks, with the expected **9,213,500 rows**.
New response bodies totaled **11,873,403,370 bytes**; the two earlier shards
were reused. No test shard was fetched. Saved manifest SHA-256:
`b63c1fcb5679e0c0fed2106db77e663bcefad755fbe5a05b1ee02996a0cb1377`.

## Streaming candidate preparation

`prepare_corpus.py` started after successful, hash-verified acquisition. It:

- Reserves all validation repository identities before scanning training, using
  case-insensitive identities, and never reads the test split.
- Reads bounded Arrow batches and writes a disk-backed SQLite index rather than
  materializing millions of commits in Python memory. SQLite/temp/cache paths
  are directed to the D: workspace, not the system drive.
- Retains the existing MIT-only **dataset-label** policy, subject length/reference
  restrictions, secret-pattern checks, whole-example generated/path exclusions,
  and conservative English action-word/generic-message heuristics.
- Uses original subjects, not silently rewritten labels. It does not add
  dedicated author-ID, author-email, or commit-timestamp columns. Original code
  context/notices can still contain public authorship information; this is not
  comprehensive anonymization.
- Counts published modifications with the official CodeT5 tokenizer in batches,
  without truncation; rejects reserved markers and estimates exceeding the
  existing 512/64 budgets. A 4,000-character coarse filter bounds tokenizer work.
- Deduplicates commit identities and exact processed modification hashes across
  splits, preferring validation. This is not a complete fork/near-duplicate audit.
- Exports **all surviving candidates**, not an arbitrary first-500 sample, with
  shard/row provenance, token estimates, repository/language distributions,
  rejection counts, and output hashes.

English action-word screening is a heuristic, not language certification or
independent human review. The dataset label is not original-source license
verification. Complete-diff token lengths can differ from these estimates.

The first filtering worker started before explicit D-drive temp settings were
transferred. That owned worker was stopped and its partial evidence retained
under `prepared-stopped-temp-settings/`; no shards were downloaded again.
The corrected filtering pass began **11:57:32.923523 UTC**, with `TEMP`, `TMP`,
`SQLITE_TMPDIR`, and cache paths inside the D: workspace. Its report confirms
`temporary_directory: D:\PushTrackML\.tmp`.

The corrected pass completed at **12:15:11.878714 UTC** (about 17m 39s):

| Split | Rows scanned | Filtered candidates | Candidate repositories |
| --- | ---: | ---: | ---: |
| Train | 7,659,458 | **743,787** | 4,708 |
| Validation | 1,554,042 | **133,228** | 589 |

All **877,015 candidates** were exported. Rejections plus candidates account for
every input row. The offline audit confirmed SQLite's quick check, zero
case-insensitive repository overlap, and both exported file hashes:

- Train: `ca061d9cd7b4d916b7caf0775560446a0260251f9f294dc11a9a73fd2bb85465`
  (1,014,492,510 bytes).
- Validation: `380cd289bb6ae8eace78b4120d294ce106a4482b90087e1fe8ea168c0613dcc9`
  (182,672,558 bytes).

The completed report SHA-256 is
`9c0ba588aebfe04f049ef0ab38c2c20e3fcb2e0430d801174df2aed3fc57fdf8`.
`prepared/offline-proof.json` also records unchanged hashes for the original
11/5 learning files and the completed training report/checkpoint. These counts
are **candidates**, not source-verified training approval.

### Important: candidates are not yet the final training set

CommitChronicle's published modifications can omit files/hunk information and
normalize meaningful code whitespace (see the existing dataset research). The
exports deliberately retain the field name **`processed_mods`**, not `diff`, and
mark every record **`training_approved: false`**. They must not be passed to the
training script as complete original changes.

The next completion gate is original-source reconstruction/verification of the
selected commits, preservation of applicable notices, full-diff token limits,
stronger duplicate/fork checks, and a target-quality audit. Batch/repository-level
Git access avoids the earlier per-commit REST API bottleneck; the separate
implementation and active source-check pass are recorded in
[experiment 0007](0007-original-source-checks.md). Do not call the large set ready
simply because download/filtering finished.

## Proof currently available

- **45 Windows data/manifest/filter unit tests passed**, including the 35 prior
  data/tokenizer regressions.
- An actual official-tokenizer batch and SQLite insertion smoke test passed
  offline on Windows.
- Acquisition completed with 73 verified shards and exact split row counts.
  Filtering completed with 877,015 candidates; integrity and split accounting
  passed the offline audit. No final training-ready count is claimed.
- No new model download, training, compression, Rust behavior/configuration
  change, commit, or push was performed.

## Windows paths and status

```text
D:\PushTrackML\data\corpus-0001\
    hub-tree.json
    shards\
    downloads\
    download-controller.json
    download.stdout.log
    download.stderr.log
    prepare-controller.json
    prepare.stdout.log
    prepare.stderr.log
    prepared\
        report.json
        candidates.sqlite3
        offline-proof.json
        train-candidates.jsonl
        validation-candidates.jsonl
        provenance\
```

`download-controller.json` reports the active attempt; the earlier
`download-process.json` is the unsuccessful detached-child attempt and must not
be treated as current. The preparation controller waits for download exit zero
and then starts filtering once. If acquisition fails, it stops instead of using
partial/corrupt input. Controllers do not restart failed work automatically.

The older 16-example learning set and `training-0001` checkpoint remain separate
and unchanged. Never replace their reports with corpus-scale claims.
