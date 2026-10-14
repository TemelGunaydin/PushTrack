# Experiment 0015: CommitBench training-data pilot

Date: **2026-10-11**. **Completed acquisition, candidate preparation, bounded
source pilot and development label review. No model training.**

The user selected CommitBench instead of the previously proposed CommitPackFT
pilot. Work stayed inline, using existing native-Windows environments and source
verification code. Frozen CommitChronicle exports, models, reviews, quality
holds and the nine unapplied target proposals were preserved.

## License and split contract

CommitBench data is **CC BY-NC 4.0**; its tools are MIT. The release card and
Zenodo metadata agree. This acquisition is for noncommercial research, not
commercial use or model-distribution clearance. Reconstructing MIT-licensed
source diffs does not erase the compiled dataset's noncommercial terms; both
licenses remain explicit in source-checked records.

- Dataset: `Maxscha/commitbench`.
- Pinned HF revision: `1500792cd6998308da046ba72b688156b2ffa471`.
- Pinned construction source: `3219f9ceb187f878b54b65121f3778f67c5dc935`.
- [Card](https://huggingface.co/datasets/Maxscha/commitbench/blob/1500792cd6998308da046ba72b688156b2ffa471/README.md),
  [release](https://zenodo.org/records/10497442),
  [paper](https://arxiv.org/abs/2403.05188).

The repository-separated Zenodo CSV (**1,495,796,508 bytes**) bundles
train/validation/test. It was **not downloaded**, so no bundled test examples
were acquired. Instead, use only the independent publisher **`train.csv`**:
**1,051,789,145 bytes**, SHA-256
`23adc5ca32088e9991882ccd252b0579b95d22d07dc9b0bce739f4e920c96f04`.

This file uses a **commit-random split**, not a repository split. Do not describe
it as a repository-separated CommitBench benchmark. Its validation/test files
and long version were not downloaded. To preserve our existing evaluation
boundaries, initial candidates are restricted to names already in the acquired
CommitChronicle training-repository universe, with current validation names and
known validation-family aliases excluded. The Chronicle test split was not
read. Names and limited metadata do not establish exhaustive fork/copy or
pretraining separation; that limitation remains.

## Train-only acquisition and full-file preparation

The pinned manifest and hash were verified natively on Windows. One successful
training CSV transfer, no automatic retry, new directory only:

- Transfer: **18:31:33–18:33:13 UTC**, all **1,051,789,145 bytes** received.
- Preparation: **18:38:54–18:41:20 UTC**.
- All **1,165,213 published training records** inspected with streaming CSV.
- **68,396 unverified candidates / 1,004 repositories** retained.
- 4,708 eligible training names; 590 reserved names after known family aliases.
- 12,173 earlier identities excluded, including source holds and pilot evidence.

`ml/prepare_commitbench.py` preserves published pair hashes, row coordinates,
source split and language metadata. It applies the existing conservative
subject/action/path/privacy heuristics, complete-looking 1–5 file headers,
duplicate screening and pinned official lossless **512 input / 64 target token**
limits. Original messages are never rewritten: the first line is the proposed
subject and the full published message remains recoverable from the frozen CSV
with its hash and coordinate. Batch tokens are checked against the official
adapter, without truncation. Candidates stay `training_approved: false`.

Preparation accounting:

| Outcome | Records |
| --- | ---: |
| Unverified candidates | 68,396 |
| Outside reserved training-repository universe | 1,005,612 |
| English/action heuristic | 65,118 |
| Subject length | 22,374 |
| Subject policy | 1,396 |
| Subject characters | 799 |
| Generic subject or mention | 447 |
| Generated path | 402 |
| Earlier identities, including holds | 273 |
| Subject reference or possible secret | 141 |
| Unsupported path or rename | 123 |
| Published token budget | 49 |
| Possible secret or control character | 48 |
| Duplicate commit or published diff | 34 |
| Reserved or unknown tokenizer token | 1 |
| **Total** | **1,165,213** |

These are policy decisions, not a population accuracy estimate or a claim that
all rejected subjects are wrong. Privacy screens are incomplete and possible
secret flags are not confirmed secret disclosures.

## Original-source pilot: 191 attempted, 117 pending

Select at most twenty repositories and ten candidates per repository in
predeclared hash order, preferring repositories not in the earlier source-checked
set. Available counts yielded **191 candidates from 20 repositories**. No target
or model outcome was used to replace a selection.

`ml/verify_commitbench_sources.py` adapts the existing Git reconstruction and
integrity auditor. Public bare Git only, exact commits/parents, no checkout or
sample execution, preserved original notices/snapshots. The phase has a
45-minute bound, two repository workers, a 1 GB local-Git storage threshold
checked between batches and the existing 20 GB disk reserve. A storage threshold
is not an exact transfer-byte cap. No authorization setup, API family sweep,
rate-limit workaround or automatic retry occurred.

Source phase: **18:44:13–18:45:03 UTC**. All 191 attempted, no budget-stop omissions;
Git storage **4,015,064 bytes**.

| Outcome | Records |
| --- | ---: |
| Original-source reconstruction and full integrity passed | 118 |
| Source commit subject failed original encoding/subject policy | 28 |
| Non-standard MIT notice | 19 |
| Missing recognized root notice | 17 |
| License path depth | 3 |
| Original subject differs from published subject | 3 |
| Possible sensitive assignment in source | 3 |
| **Total attempted** | **191** |

The 28 encoding/subject rejects do not establish corruption or bad semantics;
the source parser also enforces the original subject policy. Do not silently
relax source-subject equality to improve retention of normalized/anonymized
published messages.

All **118 reconstructed records** passed independent full-file/hunk/snapshot
application, original parent/subject and notice evidence checks, stable patch
IDs and lossless retokenization; **zero integrity errors**. One repeated changed-
text record was held by the old/new overlap checks, leaving **117 pending
records from 16 repositories**. Overlap checks also cover earlier held commits,
patches, selected validation commit/parent ancestry, file-change pairs and the
configured near-validation changed-token similarity. These are not exhaustive
semantic copy/fork/pretraining detection.

Source diffs are the complete native parent-to-commit changes, not blindly used
normalized CSV patches. Dataset provenance is explicitly changed at the adapter
boundary to CommitBench, including release license, pinned CSV hash, row index
and published pair hashes. The shared CommitChronicle verifier/auditor was not
rewritten or weakened.

## Training-target review: development evidence, not model accuracy

Read the complete diffs for the first twenty SHA-256 ranks of
`commitbench-quality-42:` plus commit identity among all 117 survivors. No
prediction filtering or replacement; no model inference or optimizer updates.

- **15 supported / 5 partially supported** subjects.
- **11 interpretation-sensitive** judgments/qualifiers.
- Two multi-file records; the rest are not proof of broad multi-file competence.
- Assistant annotation only; no independent human or blind final benchmark.

The five partial cases illustrate remaining weak supervision:

| Commit prefix | Concern |
| --- | --- |
| `6807d3665284` | Saves/unsets/restores GITHUB_TOKEN in a test; “Allow ... being set” omits test-isolation scope. |
| `4a56ad2c60f0` | Adds an output format to a command docblock; no formatter implementation is added. WP-CLI can interpret metadata, so this is not an automatic comment/behavior verdict. |
| `2a3aeff37f0e` | Removes regex lookbehind; Safari-specific motivation is outside the visible patch. |
| `5af775c57603` | Removes two requires; the claim that the module was already removed is not visible. |
| `22c8fd7378db` | Changes `if` to `elif` to prevent fallthrough; precise container type/user-handler context needs surrounding code. |

Supported examples include a named coverage server task, an expansion callback,
Python 3 byte-literal comparisons in two examples, an old UUID-key compatibility
case, test fixture permissions and an exact site-name replacement. Supported
core changes do not prove every motivation or adjective. No target was changed,
no semantic hold was applied to the frozen pending export, and the 97 remaining
subjects are unreviewed. Flags for email-like context/generated source headers
are inspection leads, not independent privacy/generated-code findings.

Different selection methods and tiny review sets mean **15/20 cannot be compared
as accuracy against the prior 24-row or twenty-output reviews**, nor prove that
CommitBench is better than CommitChronicle. No trained model has yet been
compared with CommitBench data.

## Proof and artifacts

- Eight focused native preparation tests passed before scanning.
- **28 native preparation/source/audit tests passed** before original-source work
  (includes those same eight; do not add the counts as independent tests).
- Fresh proof at **18:52:26 UTC**: SQLite quick-check `ok`; independently checked
  every one of the **68,396 candidate coordinates** against the CSV while
  confirming all 1,165,213 rows are training records; full accounting and pilot
  identity/hash proof; all 117 pending examples freshly retokenized.
- 51 earlier protected artifact hashes, both original source exports and the
  unapplied target proposals preserved. **Zero dataset label edits, zero model
  updates, no test/new validation acquisition.**

Artifacts under `D:\PushTrackML\data\commitbench-0001\`:

- `metadata/`: pinned HF tree/card, Zenodo license/file metadata, construction
  source files for inspection only.
- `download/report.json`, `train.csv`.
- `prepared/`: candidate SQLite, report, fixed source pilot, executed provenance.
- `sources-0001/`: reports/repository outcomes, reconstructed records, independent
  integrity results, snapshots/notices/Git caches, overlap holds, pending export,
  fixed quality sample and separate review, executed provenance.
- `offline-verification.json`.

| Artifact | SHA-256 |
| --- | --- |
| Candidate SQLite | `d3c1724bbe2aa2bf5edcddeeee3a8280573e32798f9f06b1a471ceb160ea43a8` |
| Fixed 191-candidate pilot | `3379dbba3b56da12b13648a56c7071d54670e65b895bdb06aebf9c9fbba7d162` |
| 117-row pending export | `7342e3769260fb9ab5930d8e3f7f5315929d97c54b97f4dae7a69bdd826f1c2b` |
| Twenty-case quality sample | `68a34b2185e92b57b5c6db02fbc800766e499d3e71d5cb0fa618e7e1cd2221e0` |
| Separate quality review | `d92a6b5ce266d0300827f8115517b4277f971a4554d1a3e570cf1205d116eb84` |
| Fresh verifier/reviewer source | `349514603c77ccbdeeb24088df77c4cd7dc1ee5b872956062d2f2d7bd9005fe0` |

Real data, annotation-bearing one-off helpers and artifacts stay outside Git.
Repository files are reusable preparation/source adapters, synthetic tests and
this report. No packages/models were acquired and no Rust application behavior,
CPU/RAM benchmark, compression, integration, commit or push occurred.

## Next decision

Historical note: the user subsequently approved the bounded expansion.
[Experiment 0016](0016-commitbench-expansion.md) completed 10,000 additional
source-checked pending examples and a separate forty-target review. It did not
train a model or change this pilot's exports/labels.

CommitBench is now a concrete, acquired candidate source, not merely a literature
suggestion. A larger **source-verified training version** can use the 68,396
candidates without reacquiring the CSV. Do not train directly on all candidates
or replace the 9,758-row historical set with the 117-row diagnostic pilot.

Next approval should specify a bounded source expansion (e.g. up to 10,000
additional complete examples), explicit handling of uncertain targets/families
and source/license holds, and a separate version/manifest. A later approved
fixed training experiment should use **every eligible row in that version**,
leave evaluation data out of gradient updates and label selection, and compare
against preserved original baselines. No reliable quality gain or product
promotion is claimed by this data-preparation experiment alone.
