# Experiment 0002: bounded, native-Windows data pilot

Executed: 2026-10-05, 07:50:46-07:52:39 UTC. Offline audit: approximately
07:57 UTC. **No training, checkpoint download, or training-data approval.**

## Question and scope

Can we obtain a small, traceable set of diff/message candidates without silently
truncating multi-file commits, trusting source-license badges, or mixing test
examples into training? All downloads, Parquet processing, tokenizer execution,
and tests ran natively on Windows. The Mac repository was used to author scripts
and issue commands over the verified SSH connection, not to host the corpus.

Workspace: `D:\PushTrackML\data\pilot-0001`.
Python: separate `D:\PushTrackML\.venv-data`, CPython 3.12.8.
Dependencies: PyArrow 25.0.1, tokenizers 0.23.2, and their dependencies; 18
packages hash-locked in `requirements-data.lock`. The existing PyTorch/CUDA
`.venv` environment was not resynchronized with these dependencies.

## Pinned inputs

CommitChronicle revision: `5fd076e67b812a9f3d1999e5e40f71715f84bb51`.
Only the first default train shard (179,224,070 bytes) and first validation
shard (153,306,487 bytes) were downloaded. SHA-256 values are fixed in
`prepare_pilot.py` and were checked after download and again offline.
No test data was downloaded.

Token counting used only `google-t5/t5-small`'s `tokenizer.json` at revision
`df1b051c49625cf57a3d0d8d3863ed4d13564fe4`, 1,389,353 bytes, SHA-256
`d2acde0d8d71dd30a711834b07781b9c89feaac33fd332f60507699282740066`.
The model card labels the repository Apache-2.0. This is a tokenizer baseline,
not a final model/deployment selection; no model weights were downloaded.

Measured response-body bytes, including small original-source requests:
**334,069,291**. This excludes HTTP/TLS overhead and package installation.
D: free space afterward was approximately 173.78 GiB.

## Candidate selection

| Split | Rows scanned | Selected candidate identities | Repositories |
| --- | ---: | ---: | ---: |
| Train | 107,018 | 1,000 | 55 |
| Validation | 16,336 | 200 | 11 |

The first-shard scan is deterministic and biased, not a representative sample
of CommitChronicle. Selection uses the dataset's MIT label, short subject and
processed-diff heuristics, 1-5 processed file changes, and a maximum of 20
candidates per repository. These are inexpensive prefilters, not validation of
original source or English quality. Candidate JSONL retains identities/splits,
not a ready-to-train message/diff corpus.

Offline checks found no selected project overlap (including case differences)
and no duplicate candidate identities. Fork-family and near-duplicate checks
remain pending; different repository names alone do not prove independence.

## Original-source verification

At most 24 checks were planned, spread across projects. **21 completed**:
9 retained for review, 12 rejected. The 22nd attempt stopped when the public
GitHub API reported 5 requests remaining; 32 API requests had been made by this
process. The run did not retry, change identities, use tokens, or bypass the
rate limit. It exited nonzero and preserved its evidence.

The nine retained examples have:

- One parent confirmed from original commit metadata.
- A full original GitHub `.diff` response, not concatenated processed dataset
  hunks. File coverage, added/deleted line counts, and hunk lengths were checked
  against commit/file metadata. Unsupported renames, mode-only changes,
  binaries, generated/vendor paths, or submodules are rejected conservatively.
- An MIT-classified root license fetched at the **actual commit revision**.
  Its full text, SHA-256, and Git blob SHA-1 were retained and verified. This is
  repository-level evidence, not clearance of every changed file's license.
- No hit from the limited secret/control-character checks. This does not prove
  absence of all secrets or personal information; no external scanner service
  or paid inference service received these records.
- At most 512 input tokens (including `summarize changes: ` and tokenizer EOS)
  and 64 target tokens. Padding/truncation were disabled. Targets are unchanged
  original first-line subjects of at most 72 characters, not generated labels.
- `review_status: pending`. Nothing was marked accepted or training-ready.

Retained: **6 train, 3 validation**, spanning 9 repositories; **1 multi-file**.
Input lengths: **187-486 tokens**.

Rejections:

| Reason | Count |
| --- | ---: |
| Token budget exceeded | 3 |
| Original subject reference/secret-policy check | 3 |
| Original resource not found (HTTP 404) | 2 |
| Missing/incomplete supported hunk representation | 1 |
| Binary/submodule change | 1 |
| Unsupported path/rename | 1 |
| Generated/vendor path | 1 |

Rejection reasons reflect this deliberately narrow pilot policy, not proof that
these commits are bad, malicious, or unusable for other research.

## Qualitative assistant review and an important tokenizer finding

The coding assistant reviewed all nine retained diffs/subjects. This was **not
an independent human annotation or legal review**:

- **5** were retained for further review because the subjects were supported by
  the visible changes.
- **4** were held for target-quality concerns: a claimed earlier fix absent from
  the diff; a vague error-related subject; an instance-attribute fix described
  as a class variable; and a vague multi-file subject omitting a version change.
- No labels were silently rewritten. The single multi-file example was held,
  so there is not yet an approved multi-file training example.

The pinned T5 tokenizer emitted **68 `<unk>` tokens out of 3,252 input tokens**
across the nine examples; seven examples contained at least one. This is
approximately 2.1%, and can discard meaningful code punctuation. Token-count
checks passing is therefore not enough to establish tokenizer suitability.
Investigate a code-aware tokenizer/model before committing to training. Changing
the tokenizer independently of pretrained weights is not a drop-in fix.

The planned 50-100-example review has **not** been reached. We have nine reviewed
candidates, not a training dataset, not a quality benchmark, and not a trained
commit-message model.

## Verification and preserved evidence

Windows checks:

- 19 offline regression tests passed before collection; 21 passed after adding
  case-insensitive split/cap tests and a valid cached-download check.
- Revalidated shard/tokenizer hashes, diff hashes, notice hashes/Git blob IDs,
  token counts, candidate caps, and split separation without network requests.
- Refused to overwrite the existing pilot directory (exit 2); the original
  report hash remained unchanged.
- Original PyTorch CUDA forward/backward proof passed again at 07:57:03 UTC.
- Data-environment setup rerun consumed the lock without new installation.

Local Windows artifacts (not committed):

- `report.json`: stop reason, counts, transfer/rate usage.
- `candidates.jsonl`: 1,200 selected identities.
- `review-pending.jsonl`: 9 original diff/subject records.
- `rejections.jsonl`: 12 completed policy/resource rejections.
- `licenses/`: original root-license notices.
- `assistant-review.jsonl`: non-approving qualitative judgments.
- `offline-audit.json`: integrity and tokenizer measurements.
- `provenance/`: collector/tests/dependency files as used for this run.

Original report SHA-256:
`87a1c1ddaac547d363625682551001ccf0a5521b347a159ae87c1c25cf887182`.
Original pending-queue SHA-256:
`47f3f99cab921e45624514d8f3c8a3c2d8b7413879cca95c0acc66e44373c3f8`.
Executed collector SHA-256:
`7321758b1513fce9b71db523ad20e65e9d19d1726cb6f23c7d153f51db508a0a`.
The current collector additionally records its source hash and case-folds
repository identities for caps/split checks; it was regression-tested but the
network acquisition was not rerun. The original run and its report were kept.

## Next gate, not an automatic continuation

Resolve tokenizer suitability/license questions; then, after the API reset and
explicit approval, expand original-source checks toward 50-100 reviewed records
using the **existing** shards and candidate manifest. Do not rerun the current
collector into a new directory just to repeat the same large downloads/checks.
A bounded resumable verification step is not implemented yet.

Per-file permissions/notices, human review, fork/near-duplicate checks, and a
proper held-out evaluation plan are still required before training. Rust
monitoring, folder configuration, Git history, and remotes were not changed.
