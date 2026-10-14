# Experiment 0004: a small learning set from the existing dataset

Date: 2026-10-05. All acquisition, data processing, and tests ran on native
Windows. **No model weights were downloaded and no training ran.**

## What we reused

The dataset is **CommitChronicle**, not a newly discovered "commitdiff" corpus.
We reused the 1,200 candidate identities, all nine previously checked records,
and the pinned local CodeT5 tokenizer assets. No Parquet shard or tokenizer
asset was downloaded again.

The immediate choice is **CodeT5-small for a local research exercise**. Its
approximately 60M-parameter size fits the original goal better than the larger
fallbacks. The model card's research-only wording remains relevant: this is not
approval for commercial deployment or distribution. See experiment 0003.

## Official tokenizer, without a custom implementation

`transformers==5.18.0` was added to the separate `.venv-data` environment;
existing pinned data dependencies were retained. The CUDA `.venv` was unchanged.
The resulting 29-package data environment is hash-locked in
`requirements-data.lock`.

We now use `transformers.RobertaTokenizer.from_pretrained` with
`local_files_only=True`. Loading the old CodeT5 special-token descriptors directly
failed because their additional-token dictionaries lack the type tag expected
by Transformers 5. The thin loader supplies those same descriptors as official
`AddedToken` objects, preserving flags, vocabulary, and IDs; it does not edit the
asset files, train a tokenizer, or implement BPE itself.

Observed: vocabulary 32,100, BOS 1, EOS 2. Complete diffs are checked for exact
round-trip preservation, unknown IDs, and the 512-token input budget. Literal
reserved markers are rejected for this tiny pilot rather than implementing a
new escaping system. Targets are at most 64 tokens/72 characters; no truncation.

## Bounded continuation

`continue_pilot.py` reuses completed identities and only retries old token-budget
rejects with the newly chosen tokenizer. It attempts at most 40 new candidates,
interleaving train/validation records, and stops after 30 pending records or the
existing public API guard. Each retained record has its full original diff,
root MIT notice at the commit revision, and snapshots of all changed files.
The source-file screen rejects detected secrets and obvious conflicting
SPDX/GPL/Apache/MPL declarations. Notices and source bytes stay local.

Run: **08:43:04-08:45:29 UTC**. It retained **16 records (11 train, 5 validation)**
and stopped at five GitHub API requests remaining, after 49 API calls. Additional
response bodies were only **524,234 bytes**; large data was not fetched again.
The report preserves the stop instead of representing the partial pass as
complete. It records 26 rejections: 13 token-budget, 7 HTTP 404, 2 root-license,
2 subject-length, 1 file-count, and 1 parent/identity check.

These are conservative screening results, not exhaustive legal clearance of
nested licenses or every third-party fragment. Repository/fork families and
near-duplicates are not fully audited. We have not established absence from
pretraining data. Do not use this set to claim held-out generalization.

## The actual small learning set

Finalized offline at **08:50:11 UTC** after the coding assistant read every
retained original diff:

| Property | Result |
| --- | ---: |
| Train examples | 11 |
| Validation examples | 5 |
| Distinct repositories | 16 |
| Multi-file examples | 3 |
| Original subjects retained | 7 |
| Explicit assistant-written replacement subjects | 9 |
| Input token range | 150-470 |
| Maximum target tokens | 16 |
| Selected repository overlap / exact duplicate diffs | 0 / 0 |

All replacements preserve `original_message` and include an annotation decision,
reviewer, and reason. For example, an instance-attribute assignment was originally
called a "class variable" fix; its replacement describes the actual assignment.
A vague "missing source link" subject was replaced with a description covering
both the SourceLink dependency and version bump. None is represented as an
original human label or independent human evaluation.

**The planned 20-50 examples were not reached.** Sixteen is sufficient for a
small mechanics/overfit exercise; collecting more is not a prerequisite for
learning the training loop. It is not enough to establish useful real-world
commit-message quality. No training execution has been authorized by these files.

Windows output:

```text
D:\PushTrackML\data\pilot-0002\learning-set\train.jsonl
D:\PushTrackML\data\pilot-0002\learning-set\validation.jsonl
D:\PushTrackML\data\pilot-0002\learning-set\manifest.json
```

The parent directory retains original pending/rejected records, MIT notices,
changed-file snapshots, and `provenance/` scripts including the explicit one-off
curation decisions. These are intentionally outside Git. Earlier experiment
records were not overwritten.

Train SHA-256:
`197ff7e95d76256c3cf5a13854cda995903e91d341c096247b4882444538d095`.
Validation SHA-256:
`d0a84bf9f54c98e4d8be9233aefba2908f3fd2360503587a07b57fa88e54b70c`.

## Proof and next bounded exercise

**35 offline regression tests passed on Windows.** Finalization additionally
verified source/notice/diff hashes, preserved originals, tokenizer fidelity,
length limits, split separation by project name, and duplicate identities/diffs.
It made no network requests. Rust monitoring/configuration were unchanged.

Proposed next step, requiring approval: download the pinned CodeT5-small weights
(**242,026,427 bytes**, approximately 242 MB), load them with a safe weights-only
path, record a baseline, then run a fixed short training-loop demonstration on
the 11 training examples. Keep the five validation examples out of gradient
updates; do not tune or claim quality from such a tiny validation set. Record
actual losses and predictions and stop. No compression, deployment, or publish
integration is part of that first exercise.

Read-only metadata identifies the checkpoint as `pytorch_model.bin` at
`b1ee9570c289f21b5922b9c768a1ce12957bf968`, LFS SHA-256
`968fb0f45e1efc8cf3dd50012d1f82ad82098107cbadde2c0fdd8e61bac02908`.
It was **not** downloaded. Never enable arbitrary pickle execution or remote
model code merely to load it; validate the hash and use the appropriate safe
loader when the download/training step is approved.
