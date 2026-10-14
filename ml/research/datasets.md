# Dataset research: Git diff -> English commit subject

Historical initial research. For the 2026-10-11 post-training comparison and
newer dataset leads, see [data-improvement-options.md](data-improvement-options.md).
Acquisition statements below describe the original review date, not the later
completed CommitChronicle collection/training experiments or the subsequently
selected [CommitBench pilot](../experiments/0015-commitbench-pilot.md).

Reviewed: 2026-10-03. This is research and a proposed next step, not a dataset
license acceptance, download, or training result. Only small cards, source files,
and metadata were fetched. No corpus/shard/checkpoint was downloaded; the Windows
training environment was not changed.

## Recommendation

**CommitChronicle is the best candidate to inspect first**, because it retains
commit identities, repository licenses, multiple file modifications, and
project-separated train/validation/test splits. Use it as a candidate index,
not an automatically approved collection of complete, unmodified Git patches.

For the first pilot, propose a ceiling of 1,000 candidate training commits
spread across repositories, with a cap per repository, plus separate validation
candidates from the provided validation split. Begin with a manual review of
50-100 examples before enlarging the pilot. These are acquisition limits, not
promises about how many examples survive filters or about resulting quality.

Before acquiring data, agree on the source-license policy and model/tokenizer
revision. MIT-only is a conservative initial source allowlist for operational
simplicity; it is not a legal guarantee. Verify applicable licenses at the actual
source commit, preserve notices/attribution, and exclude ambiguous cases.

For each accepted candidate, recover/verify the original full commit diff and
parent from its upstream Git repository. Keep every changed file or reject the
whole example; never quietly drop files to satisfy token limits. Exclude merges,
binary/unsupported changes, secrets, generated output, ambiguous English, and
messages that depend on information absent from the diff. The message's first
line is only a proposed subject, not an automatically faithful label.

Respect the existing project splits, verify repository/fork separation and
patch deduplication independently, and do not train on test-only subsets. Count
tokens with the selected tokenizer without truncation; reject/report inputs
above the proposed 512-token pilot budget rather than losing commit coverage.
Dataset format and input-token statistics affect quality; dataset size alone
does not determine end-user inference RAM.

## Comparison

| Source | Input and metadata | Licensing evidence | Decision for this project |
| --- | --- | --- | --- |
| CommitChronicle | 10,699,767 default rows; commit-level `mods`, repo/hash/license, original and processed messages; project-separated splits | Card says `other`; source collection targets MIT, Apache-2.0, BSD-3-Clause and explicitly requires original-license compliance | Preferred candidate index, pending source permissions and completeness checks |
| CommitPackFT | Before/after contents and paths for one file; subject, repo(s), commit and license; language-specific shards | MIT release metadata plus separate per-source licenses, including unknown/copyleft identifiers in documentation | Small diagnostic alternative; not proof of multi-file capability |
| CommitBench | 1,664,590 examples; complete commit patch extraction; six programming languages; English-oriented filters | Dataset CC BY-NC 4.0; tooling MIT | Useful noncommercial research benchmark, not the default foundation for possible commercial application use |
| MCMD | Paired diffs/messages, hashes/times and repository identities; five programming languages | Zenodo API declares CC BY 4.0; upstream source-code permissions still need review | Too large and insufficiently source-license-audited for the first pilot |
| Long Code Arena CMG | 163 manually curated large Python commits from 34 repositories, derived from CommitChronicle test data | Apache-2.0 dataset metadata; source repositories have separate licenses | Possible later stress evaluation, not a small-context training set |

These are metadata/published-code observations, not a row-by-row audit. Academic
citation is not a substitute for permission or preservation of license notices.
A free application is not automatically a noncommercial use. Do not infer a
trained model's distribution rights solely from a dataset badge; review the
actual terms and intended use before release.

## CommitChronicle: important details

[Card at reviewed revision](https://huggingface.co/datasets/JetBrains-Research/commit-chronicle/blob/5fd076e67b812a9f3d1999e5e40f71715f84bb51/README.md).

- Default: 7,659,458 train, 1,554,042 validation, 1,486,267 test examples.
  Additional configurations are overlapping test subsets, not extra distinct
  training rows. The card reports approximately 14.2 GB of downloads and
  41.7 GB of decoded default data; a full download is unnecessary for the pilot.
- `mods` lists file changes and paths; `repo` and `hash` support independent
  recovery from Git. `language` is the repository's main programming language,
  not necessarily the language of every changed file.
- The card warns that public source code can still contain personal information
  and credentials. Do not feed author IDs, emails, commit hashes, dates,
  `original_message`, or target text into the model input.
- The published [diff processor](https://github.com/saridormi/commit_chronicle/blob/c6ca5c70fa4c05bc4222dc9743492051b1c11a6c/src/processing/diff_processor.py)
  strips lines, removes some hunk headers, squeezes whitespace, and retains only
  string/ASCII file diffs. It can drop a modification while retaining the rest
  of the commit. Consequently, processed `mods` are not guaranteed to be a
  complete applyable unified patch; naively adding headers cannot restore lost
  files, indentation, or hunk information.
- The [message processor](https://github.com/saridormi/commit_chronicle/blob/c6ca5c70fa4c05bc4222dc9743492051b1c11a6c/src/processing/message_processor.py)
  uses ASCII filtering, not a natural-language detector. ASCII does not prove
  English. `original_message` remains a separate field; processed-message
  cleaning does not sanitize it.
- The published [configuration](https://github.com/saridormi/commit_chronicle/blob/c6ca5c70fa4c05bc4222dc9743492051b1c11a6c/configs/process_data.yaml)
  enables outer duplicate removal for training, not all split pairs. Verify
  validation/test overlap and near-duplicates ourselves. Project splits do not
  automatically prove fork-family or pretraining-corpus separation.
- The approximately 5.1 MB `subset_llm` file contains 4,025 **test** rows. Do
  not choose it for training just because it is small. Actual Parquet streaming
  can still read/download substantial shard data; budget transfer and cache use
  rather than assuming a 1,000-row sample costs only 1,000 rows on the network.

Collection paper: [Eliseeva et al., ASE 2023](https://arxiv.org/abs/2308.07655).
Published source review can identify risks; it does not prove each released row
was generated with the exact latest source revision. Verify sampled records
against original commits before claiming complete-commit coverage.

## CommitPackFT: small alternative, incomplete-commit risks

[Card](https://huggingface.co/datasets/bigcode/commitpackft),
[loader at reviewed revision](https://huggingface.co/datasets/bigcode/commitpackft/blob/fc56fe33c030c6daa414c2b112c932b8eed085e6/commitpackft.py),
[OctoPack paper](https://arxiv.org/abs/2308.07124).

The card lists 702,062 examples and 277 language/file-type categories. It lists
2,996 Rust examples; we have not independently counted downloaded rows.
At the reviewed revision the plain JSONL Rust shard metadata reports 7,411,711
bytes, versus 135,858,935 bytes for Python. This makes Rust attractive for an
initial ingestion/overfit exercise, but the count of accepted licensed,
English, short, and faithful examples is unknown.

The loader merely yields before/after contents, paths, commit, source license,
and repository names into a train split. It does not validate licenses or
complete commit coverage, and the release does not supply a held-out project
split. `repos` may contain comma-separated names; account for repository/fork
families rather than treating that string as one unrelated repository.

The paper describes excluding multi-file commits. However, the published
[SQL stage 4](https://github.com/bigcode-project/octopack/blob/e17a8f6470264286bc6a52eb8263582083bf3bf6/dataset/commitpack/sql/sql_4_commits_table_dedup_files.sql)
first retains only records with non-null, equal old/new paths; then
[stage 5](https://github.com/bigcode-project/octopack/blob/e17a8f6470264286bc6a52eb8263582083bf3bf6/dataset/commitpack/sql/sql_5.sql)
counts those remaining records. This is not a check that the original commit
changed exactly one file: added/deleted/renamed files can have been removed
before counting. Do not conclude every released row captures the whole commit.
This is a limitation of the reviewed construction code, not a measured count
of affected released examples.

[SQL stage 1](https://github.com/bigcode-project/octopack/blob/e17a8f6470264286bc6a52eb8263582083bf3bf6/dataset/commitpack/sql/sql_1_commits_table_base.sql)
allows AGPL/LGPL/MPL/EPL alongside MIT/Apache/BSD and others. The dataset's MIT
label cannot erase source obligations. Only ingest an explicitly reviewed
subset; reconstruct a file diff locally without executing sample code, and
verify original commit coverage before making full-commit training claims.
Do not run old custom dataset scripts with remote-code trust to save effort.

Rust shard LFS SHA-256 metadata:
`5611f3701026acf3c43ba64da50f4f65a078e84fba56e2bf313e8f2996b0cc68`.
This is a future integrity reference, not evidence that the shard was downloaded.

## CommitBench: good benchmark with a noncommercial condition

[Card at reviewed revision](https://huggingface.co/datasets/Maxscha/commitbench/blob/1500792cd6998308da046ba72b688156b2ffa471/README.md),
[Zenodo record](https://zenodo.org/records/10497442),
[paper](https://arxiv.org/abs/2403.05188).

The card explicitly distinguishes **CC BY-NC 4.0 data** from **MIT code**.
Source-repository selection was based on CodeSearchNet and MIT licensing,
but this does not remove the released dataset's noncommercial condition.

The [extractor](https://github.com/Maxscha/commitbench/blob/3219f9ceb187f878b54b65121f3778f67c5dc935/create/dataset_from_repo.py)
uses the full parent-to-commit patch and excludes initial/merge commits. The
[pipeline](https://github.com/Maxscha/commitbench/blob/3219f9ceb187f878b54b65121f3778f67c5dc935/run_pipeline.sh)
sets standard diff limits to 511 tokens and long-version limits to 2,047;
message limits are 8-128 tokens. Recount with our selected tokenizer/subject
format; do not assume the benchmark's filter matches our eventual input.

The [exporter](https://github.com/Maxscha/commitbench/blob/3219f9ceb187f878b54b65121f3778f67c5dc935/exporter/to_csv_split.py)
shuffles rows and assigns 70/15/15 splits, rather than holding out repositories.
It deduplicates `(message, diff)` pairs, not every identical diff with a different
message. Zenodo offers a separate `commitbench_by_repo.csv`; do not mistake the
ordinary Hugging Face split for it or assume near-duplicate removal is complete.

Zenodo API sizes: standard CSV approximately 1.50 GB; by-repository CSV 1.50 GB;
long CSV 6.77 GB; accompanying `licenses.json` approximately 579 MB. None was
downloaded. Even the license companion is not a tiny lookup file.

## MCMD and Long Code Arena

[MCMD archive](https://zenodo.org/records/5025758),
[structure documentation](https://github.com/DeepSoftwareAnalytics/CommitMsgEmpirical/blob/main/dataset/ReadMe.md).
The archive API explicitly reports **CC BY 4.0**. Initial web results did not
establish the license; direct metadata resolved that uncertainty. Do not state
that MCMD has no dataset license. This still does not establish license coverage
for every included source repository/file.

The archive lists 39,454,259,700-byte raw and 10,786,563,545-byte filtered tarballs.
Raw records are pickle files; never unpickle untrusted downloaded data. Filtered
parallel text has repository/hash/time information but is preprocessed. Neither
format is necessary for our bounded first pilot.

[Long Code Arena card](https://huggingface.co/datasets/JetBrains-Research/lca-commit-message-generation/blob/7079c26e313f8376249f2b0368bef9830494f055/README.md)
describes 163 curated large commits from 34 repositories. All are test data,
derived from CommitChronicle's Python test split. It is useful for later large-
commit/abstention stress testing; most examples may exceed a 512-token budget.
Report exclusions instead of silently truncating. It must not become a training
set or leak into tuning. Preserve upstream notices despite Apache-2.0 metadata.

## Research boundary and next approval

No candidate is approved for unrestricted use by this note. The next bounded
implementation is a reviewed, storage-budgeted pilot collector with provenance
and rejection reports, not bulk download or training. The model/tokenizer
license decision also remains open. CommitPackFT Rust is a smaller alternative
if the immediate goal is teaching ingestion mechanics rather than multi-file
summarization; label that limitation explicitly.
