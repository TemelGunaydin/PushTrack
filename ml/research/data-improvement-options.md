# Training-data improvement options after the six-epoch run

**Subsequent user decision:** use CommitBench, not the proposed CommitPackFT
pilot. See [experiment 0015](../experiments/0015-commitbench-pilot.md) for the
completed train-only acquisition/preparation and bounded source review; the
later [expansion](../experiments/0016-commitbench-expansion.md) added 10,000 pending
examples without model training. The recommendations and no-download statements
below record the earlier research
stage, not the later authorized work. Noncommercial terms remain explicit.

Reviewed: **2026-10-11**. Primary cards, papers, release documentation and metadata
only; no new corpus/shard/model download, archive inspection or test-row access.
Published counts below were not independently recounted. This note does not
approve acquisition, licensing, label changes, model promotion or training.

## Answer: better and broader data can help

The completed six-epoch recipe reduced train loss while validation loss rose
after epoch 3, and semantic results remained mixed. That does **not** show that
more training data would be useless. More distinct, relevant and correctly
labelled examples can reduce reliance on project-specific patterns and supply
examples of changes the model currently confuses. This remains a hypothesis
to test, not a guaranteed gain; model capacity, representation, the 512-token
input limit and imperfect metrics also matter.

The immediate objective is **complete diff -> visible, faithful short subject**,
not recovering an author's undocumented motivation. Human-authored messages,
Conventional Commits syntax, a what/why label, and high automated filtering rates
do not by themselves prove that a target follows from its paired diff.

## Practical shortlist

| Source | Potential benefit | Important limitation | Current recommendation |
| --- | --- | --- | --- |
| [CommitPackFT](https://huggingface.co/datasets/bigcode/commitpackft) | 702,062 published examples; instruction-like subject filtering; 277 language/file-type categories; before/after file content | Original purpose is instruction-based code editing, not fully human-verified CMG targets. Single-file focus; original whole-commit coverage must be rechecked. Release MIT metadata does not settle each source's license. No project-disjoint holdout supplied. | **First external pilot candidate**, using a pinned, source-checked MIT subset, not the whole release blindly. |
| Existing [CommitChronicle](https://huggingface.co/datasets/JetBrains-Research/commit-chronicle) candidate pool | Already acquired; much more potential training data than the 9,758 prepared rows; multi-file and published project splits | Processed mods can omit content; original subjects remain weak supervision. Extra records still require original Git reconstruction and quality checks. | Expand selectively without downloading another bulk index if this yields cleaner/diverse examples more efficiently. |
| [CommitBench](https://huggingface.co/datasets/Maxscha/commitbench) | 1,664,590 published diff/message pairs; task-aligned filtering, separate repository-split archive | Data **CC BY-NC 4.0**, tooling MIT; no human annotators. Default split is by commit, not project. | Useful research comparator where terms fit; not the default foundation for possible commercial distribution without clearance. |
| [CommitSuite](https://github.com/security-pride/CommitSuite) | Newer corpus, approximately 63K commits; conventional-message and what/why annotations | Counts/repository totals conflict between README and paper sections; LLM labels with human spot checks are not gold targets. Explicit dataset-release license was not established; evaluation subsets overlap the full corpus. | Research lead; hold until license/version/split/completeness questions are resolved. |
| [ApacheCM / C3Gen](https://zenodo.org/records/15502318) | Larger Apache-project corpus, broader repository histories; original paper reports about 235K commits | Published partition totals conflict with headline size; no verified project/time-disjoint split or whole-patch completeness guarantee. Dataset-specific license not established in this review. | Not a ready drop-in replacement. Apache in the name is not proof of an Apache-2.0 release license. |

CommitPackFT's published Rust shard is approximately **7.4 MB / 2,996 examples**
at the revision recorded in [the earlier research](datasets.md). These are
published/metadata figures, not an accepted-example count. A small shard is a
cheap way to test ingestion/quality assumptions, not evidence that a Rust-only
subset improves a multilingual model or that millions of examples are required.

## Quality and coverage caveats that matter here

### CommitPackFT

The [OctoPack paper](https://arxiv.org/abs/2308.07124) describes a filtered,
instruction-oriented single-file corpus, not exhaustive human correction of
message/diff pairs. Our earlier inspection of the published construction SQL
found path/non-null filtering **before** counting remaining files. Thus deriving
a patch that applies to one file from before/after contents does not prove the original
commit had no other changes. Reconstruct original parent-to-commit coverage;
keep every changed file or reject the example. Do not run old remote dataset
loader code just because it is included in the release.

The card's MIT badge is not blanket clearance for all input code: its documented
source-license values include unknown/copyleft identifiers. This does not prove
which values occur in a selected shard. Inspect selected records and original
source notices; preserve attribution and quarantine ambiguous cases.

### CommitSuite

The [paper](https://arxiv.org/abs/2605.02256) and repository documentation report
63,533 versus 63,581 commits, with 172 versus 243 repositories in different
sections. Do not silently choose a convenient total. Documentation describes
per-file diffs and AST information, but this is not proof of lossless complete
Git-patch coverage for every row.

DeepSeek-V3 supplies what/why labels. The paper reports spot checks of 182 good
messages and 500 annotations, plus a separate evaluator audit; these are not
full-corpus human validation. Messages in lower quality classes remain present.
Even a message with an explicit why can depend on information absent from the
model input. The full corpus includes the material from which evaluation
subsets were sampled; do not merge them into training and call the result held
out. No explicit dataset-release license was verified from the visible root
and README. Upstream permissive-license selection does not settle release terms.

### ApacheCM

The [C3Gen paper](https://arxiv.org/abs/2507.17690) reports 234,799 commits from
50 repositories, but its partition table totals 269,830. The
[CoRaCMG paper](https://arxiv.org/abs/2509.18337) also does not settle that
contradiction. Descriptions of standard diffs, line-count filtering and a full
schema do not establish complete-file coverage. The documented random test
sampling is not proof of repository-disjoint or strict chronological separation.
The human study examines a sampled evaluation set, not every training target.
The release archive was not downloaded and dataset-specific terms remain
unverified here; no permission is inferred merely from Apache-project provenance.

## Useful adjacent resources, not positive CMG data by default

- [CodeFuse-CommitEval](https://github.com/codefuse-ai/CodeFuse-CommitEval) is a
  **message-code inconsistency** resource. Its [paper](https://arxiv.org/abs/2511.19875)
  describes 52,127 pairs including **19,967 deliberately mutated inconsistent
  messages**. Never feed those mutations as correct generation targets. It may
  later inform a consistency evaluator, a different task. It is evaluation-
  focused, but no blanket legal training prohibition was established in the
  inspected documents. Tooling is Apache-2.0, whereas the separately hosted data
  terms were not reliably verified: artifact-card access failed, and the latest
  metadata check did not expose an HTTP status. No mirror or quota workaround
  was used.
- [Commit-message-quality](https://huggingface.co/datasets/saridormi/commit-message-quality)
  has 1,564 quality-labelled messages according to its card, but is not a ready
  diff-to-subject pair corpus. Message style/quality classification cannot by
  itself catch an otherwise plausible subject attached to the wrong action.
- [Long Code Arena CMG](https://huggingface.co/datasets/JetBrains-Research/lca-commit-message-generation)
  is the curated **test-only** collection derived from CommitChronicle's test
  split. Keep it out of training and tuning; no test records were read here.

## Proposed bounded next step — approval required

Pilot **CommitPackFT**, not an immediate bulk merge or training run:

1. Use the pinned revision and Rust shard identity already documented in
   `datasets.md`; verify current metadata before an approved download. Cap the
   shard transfer at **10 MB**. Do not download models or install packages.
2. Treat records as candidates. Examine at most **200 candidates / 20 source
   repositories**, not a promise of 200 accepted examples. Use existing Windows
   environments, caches, tokenizer and source-verification code.
3. To protect untouched evaluation boundaries when mixing corpora, initially
   restrict candidates to repository names already assigned to the acquired
   CommitChronicle **training** partition. Exclude existing validation names,
   duplicate commits/patches and ambiguous family identities. Do not read the
   test split to make more examples eligible. Name separation alone is not
   exhaustive fork/pretraining-contamination clearance.
4. Allow only the existing reviewed MIT source policy; verify original commits,
   parents, whole changed-file coverage and notices. A bounded public-Git phase
   needs explicit approval: propose **45 minutes**, a **1 GB local-cache stop
   threshold checked between batches**, and the existing 20 GB disk reserve.
   That storage threshold is not an exact network-byte cap. No authentication
   setup, repository-metadata sweep, rate-limit workaround or automatic retry.
5. Enforce full-diff 512 / subject 64 official token limits, source/privacy
   screens, provenance and overlap checks. Reject rather than truncate or drop
   files. Record source-access failures and retained/rejected counts honestly.
6. Review accepted target semantics before proposing a new training version.
   Compare what is gained over the existing pool; a different dataset name is
   not an independent source if it repeats the same GitHub commits.

No download or source acquisition above has started. Any future combined
training set must preserve old evidence and have an explicit manifest/recipe;
it must not silently replace the existing 9,758 examples with a small pilot.
The nine [target proposals](../experiments/0014-target-proposals.md) remain
separate and unapplied. Neither that cleanup nor external data guarantees that
CodeT5-small has adequate capacity for every intended commit.
