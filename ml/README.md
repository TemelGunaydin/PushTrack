# Local commit-message experiment

**Status: resumed on 2026-10-13; a verified local editable-draft model prototype
is available. Qwen3.5-4B Q4_K_M (2.74GB), Apache-2.0, runs on demand with the
pinned MIT llama.cpp CPU runtime. The Rust dashboard now has an experimental
on-demand staged-only editable `m` action; see [integration evidence](experiments/0021-pushtrack-local-drafts.md).**

[Selected-model evidence and usage](experiments/0020-verified-local-draft-model.md):
18 usable / 2 needs-edit / 0 misleading on 20 reused development cases; 12 faithful
synthetic core changes. Seven judgments are interpretation-sensitive, not independent
human gold or population accuracy. Fresh reload reproduced six hard outputs;
complete-input/context/control checks and 18 native connector tests passed.
The [`local_subject.py`](local_subject.py) stdin connector prints one reviewable
English draft, checks the pinned model hash, and never downloads/commits/pushes.
Rust embeds the same connector; asset/runtime setup is explicit and optional.
One native Windows Rust-exported synthetic diff took19.33s in the connector and
~4.55GB sampled aggregate Python/C++ working set. This is not a Mac/Linux or
whole-dashboard performance guarantee. A separately approved actual Mac ARM64
TUI proof now passed generation/edit/Enter stale refusal/Esc/Ctrl+C cleanup;
[Mac evidence](experiments/0024-mac-native-drafts.md): one small cache-warm example
17.77s and5.99GB sampled aggregate Rust/Python/C++ RSS, not broad accuracy, a
latency distribution or Linux deployment proof.
Asset/policy metadata: [`local-model.json`](local-model.json).

[Complete-input capacity flow](experiments/0027-draft-capacity.md) raises capture
to4MiB. Default context stays4096; exact whole-prompt token counts (raw diff plus
unchanged literal audit) recommend larger supported contexts only after explicit
Enter approval. No completion on oversized default prompts.60Rust/23Python tests,
PTY confirmation/cancel tests and an actual4k tokenizer-only large synthetic
input proof passed. Long-context generation/resource/accuracy remains unverified;
prior quality judgments are not extended to larger input. The separately approved
[lossless token-boundary candidate](experiments/0030-lossless-literal-token-boundaries.md)
is now [installed in the experimental CLI](experiments/0032-literal-token-cli-installation.md);
literal text alone no longer triggers the old input refusal, while control bytes
remain unsupported. Before installation the candidate
passed33Python/60Rust tests, task-only draft/terminal PTY checks and44small native
4096tokenization-only cases, excluding all33special source IDs with exact byte
roundtrips and four marker-free native legacy-ID matches. A separately approved
[three-case generation probe](experiments/0031-literal-input-generation-probe.md)
produced two accepted drafts and one unchanged internal-summary marker refusal;
no retry or gate relaxation. This is not all-cases semantic success or promotion.
Private staged-scope measurement was **not performed**. User-approved CLI
replacement subsequently passed full installed-binary PTY with fake transports;
its available space exceeded the unchanged download-fixture reserve, closing the
earlier unavailable PTY gate. No real generation/download occurred during install.
Chunk count/time amplification and output guards remain bounded; no escaping,
omission or unsafe fallback.
The stopped research training and native data/checkpoints are untouched.

The [installed timeout/modal update](experiments/0033-bounded-timeouts-and-modal-focus.md)
shares the remaining300s job budget with completion instead of a separate120s cap;
startup120s/preparation60s and all source/output guards remain. Errors name safe
endpoint/stage information.41Python/62Rust tests and full release/installed fake-
transport PTY passed. Modals dim the background and use shorter draft explanations.
**No real/private large-context generation was retried or verified.**

The dashboard also has an explicit **`a` model/source selection** flow, a real
byte-progress gauge, SHA-256 verification, resumable/cancellable acquisition and
an existing-file selection option. [Model-store evidence](experiments/0022-model-store.md).
**GitHub v2 publication is complete:** [asset-only prerelease](https://github.com/TemelGunaydin/PushTrack/releases/tag/model-qwen35-4b-q4km-v2)
contains six <=512MiB byte pieces and pinned notices, all11assets verified.
[Publication/download evidence](experiments/0023-model-store-publication.md).
The earlier v1 failed draft remains preserved. The TUI downloader is enabled;
actual public Mac TUI acquisition passed cancel/resume, exact prefix and all full
model/piece/license SHA-256 checks without inference or Git writes.52Rust tests,
strict Clippy, release build and updated PTY checks passed. Native v2 packaging
kept the original model and139protected artifacts unchanged.
No training resumed, new quality judgment or actual-model Unix inference proof is claimed.

The [100-epoch research run](experiments/0018-commitbench-hundred-epochs.md) remains
user-stopped during epoch 72, with 71 measured epochs/checkpoints retained. Its
125,000-update plan was not completed or promoted; verification remains pending.
Checkpoints lack optimizer resume state. No automatic restart or exact optimizer
continuation is claimed. Earlier [pause evidence](experiments/0019-local-subject-and-pause.md)
and all rejected candidates remain preserved.

The latest completed [CommitBench three-epoch comparison](experiments/0017-commitbench-training.md)
used all 10,000 records: 3,750 updates / 30,000 exposures, fresh verification and
fixed-case review. No promotion or automatic extension followed; the later
100-epoch run required the user's explicit new request.

Final validation loss was **3.2373**, worse than the historical Chronicle
three-epoch recipe's **3.1262** on the same 962 development rows. The reused,
unblinded twenty-case assistant review found **5 usable / 10 edit-needed /
5 misleading** subjects versus the previous **6 / 7 / 7**; this mixed result is
not population accuracy or demonstrated superiority. Forty-six native tests
passed; all three checkpoints and every training exposure were verified, and
16 final predictions reproduced in a fresh process. False quality-approval
flags, all original targets and thirteen unapplied proposals remain unchanged.
No new acquisition, test access, CPU/RAM profiling or Rust integration occurred.

### Historical Chronicle comparisons

The earlier [six-epoch comparison](experiments/0013-six-epoch-comparison.md),
used all 9,758 historical training examples six times. Lowest validation loss
selected epoch 3 (3.1181); final epoch 6 worsened to 3.1896 while train loss kept
decreasing. Semantic outcomes remain mixed, not reliable or production-ready.

On the same twenty previously reviewed development cases, the old model had
6 usable / 7 edit-needed / 7 misleading subjects. The new loss-selected model
had **5 / 9 / 6**; a separately identified post-run review of final epoch six had
**6 / 8 / 6**. These are unblinded assistant judgments, with interpretation-sensitive
cases, not population accuracy. Some property/TODO descriptions improve, while
serious errors such as calling a blacklist a whitelist remain. No further epochs
or product promotion followed automatically.

A [training-target proposal](experiments/0014-target-proposals.md) now records
nine possible corrections/clarifications separately, with original labels and
all 9,758 rows unchanged. Whole-set heuristics produced 373 inspection leads,
not 373 confirmed errors. Ten focused tests and fresh native tokenizer/identity
checks passed; no proposal was applied or training performed during that
proposal-only step.
The user subsequently selected **CommitBench**. Its
[training-data pilot](experiments/0015-commitbench-pilot.md) acquired only the
pinned training CSV and screened all 1,165,213 rows, initially retaining 68,396
unverified candidates. A bounded source pilot produced 117 integrity-checked
pending records; a fixed twenty-target assistant review found 15 supported and
five partially supported subjects. CommitBench data is **CC BY-NC 4.0**;
noncommercial research use does not establish commercial/model-distribution
clearance. No test CSV was acquired and no original labels changed.

The subsequently approved [source expansion](experiments/0016-commitbench-expansion.md)
reached **10,000 additional pending records / 344 repositories**. All passed
source/patch/tokenizer gates; fresh proof re-applied 10,750 file patches and
retokenized every record. The separate forty-target review found **29 supported /
11 partially supported** subjects, with 17 interpretation-sensitive judgments
and four unapplied wording proposals. This is not model accuracy or a full
semantic audit: **9,960 targets remain unreviewed**, repository-family coverage
is incomplete. The separately approved [research comparison](experiments/0017-commitbench-training.md)
used the complete pending set, not just forty examples, with original labels;
research permission did not promote its quality flags.
The earlier [alternative-data recommendation](research/data-improvement-options.md)
for CommitPackFT is superseded by this explicit dataset choice.

The [decoding/label diagnostic](experiments/0012-quality-diagnostics.md) did not
support adopting four-beam search: the reused twenty-case assistant review
worsened from 6 usable / 7 edit-needed / 7 misleading to 4 / 6 / 10. Training-only
inspection found useful references and some concrete label errors; no records
were removed or labels rewritten.

The completed [three-epoch comparison](experiments/0011-three-epoch-comparison.md)
passed fresh-process verification. Validation loss improved from 3.2190 (the old
one-epoch recipe) to 3.1262; exact matches remained 0/962. Its mixed semantic
results did not establish product readiness.

The completed [one-epoch run](experiments/0009-corpus-training.md) used 9,758 train /
962 validation examples (1,220 updates). Validation loss improved from 8.6991 to
3.2190, but exact matches remained 0/962. Its saved checkpoint passed a
fresh-process 16-example reload proof; production quality is unproven.

A [20-example diff-grounded assistant review](experiments/0010-model-quality-review.md)
judged **3 usable, 12 needing edits, and 5 misleading**. These sample judgments
are not population accuracy or independent human annotation. The separately
approved three-epoch run is complete. The user subsequently requested continued
quality improvement; the six-epoch comparison is now finished at its declared
stop. Product integration and additional experiments are not authorized automatically.

The earlier 100-step exercise memorized 8/11 training subjects while validation
loss worsened (0/5 exact matches). Its checkpoint was not the starting point for
larger runs; none of these experiments establishes a production model.

[Full-corpus filtering](experiments/0006-corpus-preparation.md) completed across
9.21M train/validation records, retaining **743,787 + 133,228 candidates**.
[Original-source collection](experiments/0007-original-source-checks.md) reached
10,000 + 1,000 examples. The [full integrity audit](experiments/0008-corpus-audit.md)
passed for all 11,000; quality holds leave **9,758 + 962 pending candidates**.
Canonical/fork metadata is incomplete and most labels remain unreviewed. The
user subsequently authorized a bounded research training run with these limits
explicitly documented; historical data-quality flags are not silently promoted.

This is an isolated learning experiment, not an available PushTrack command.
The Rust dashboard still never commits or pushes. Windows support here applies
only to these Python experiments, not to the Rust application.

## Goal and boundaries

Learn to fine-tune a compact encoder-decoder model for:

> Already-selected Git diff -> one short, faithful English commit subject.

The first model will not select files, decide commit boundaries, execute Git,
commit, or push. Do not put a model in the dashboard refresh loop. Any future
inference should run only on demand and release memory when its process exits.
A future publish command would separately require an explicit preview and
confirmation; it is not implemented.

Training hardware and deployment requirements are different. Training uses an
RTX 4070 with 12 GB VRAM and 64 GB system RAM. Deployment must work locally on
CPU with a measured, small RAM footprint and no paid inference API. Do not ship
this CUDA/PyTorch environment to end users.

## Step 1: reproduce the Windows environment

Requirements: native Windows x64, an existing 64-bit Python 3.12 installation,
[uv](https://docs.astral.sh/uv/), and a compatible NVIDIA driver. Neither Ubuntu,
Docker, nor a separately installed CUDA toolkit is needed. The tested driver is
616.92; the selected official wheel contains CUDA 13.0 runtime libraries.
`nvidia-smi`'s CUDA version describes driver capability, not an installed Python
framework or a requirement to use that exact runtime version.

From this directory in PowerShell:

```powershell
.\setup-windows.ps1 -Workspace 'D:\PushTrackML'

& 'D:\PushTrackML\.venv\Scripts\python.exe' .\check_environment.py `
    --output 'D:\PushTrackML\runs\environment.json'
```

The script uses your existing Python and uv. It resolves WinGet symbolic links
because the uv link may fail to execute in Windows OpenSSH sessions. The first
Python on PATH must be Python 3.12; other environments, including Conda, are not
modified. An existing environment of the wrong version is rejected, not erased.
The script does not change execution policy, PATH, shell profiles, or registry
settings. Review any local script-policy restriction rather than disabling it.

All large files stay in the workspace:

| Path | Purpose |
| --- | --- |
| `.venv/` | CUDA environment-proof packages |
| `.venv-data/` | Separate data/tokenizer packages |
| `.venv-train/` | Separate pinned training packages |
| `.cache/uv/` | Package downloads/cache |
| `.tmp/` | Installation temporary files |
| `runs/` | Local proof records; later, experiment outputs |

uv cache and temporary-directory settings are process-local and restored after
setup. No Python installation is downloaded and no system Python packages are
changed. The script can be rerun to synchronize the same environment. Do not
point `Workspace` at an unrelated environment: synchronization removes packages
that are not in this experiment's lock.

`requirements-windows.in` pins only torch; dependencies are frozen with hashes
in `requirements-windows.lock`. This is a **Windows x64 / Python 3.12 lock**, not
a universal Mac/Linux environment. Setup consumes the lock with hash validation
and disables source builds. If the lock is absent, setup resolves it once using
the official [PyTorch CUDA 13.0 index](https://download.pytorch.org/whl/cu130/).
Do not remove or regenerate the lock silently for a recorded experiment.

The GPU check performs a 256 x 256 float32 matrix multiplication and computes
its gradients. Both are checked against exact expected values. Missing CUDA
fails with a nonzero exit code; there is no silent CPU fallback. It does not
load a checkpoint, optimize model weights, or measure inference performance.
The process exits after the check, releasing its CUDA allocations.

The CUDA-proof `.venv` environment does not contain NumPy, Transformers, tokenizers, dataset
libraries, or export tools. The tested torch import warns about missing NumPy;
that does not prevent the native tensor/gradient checks. Step 2 installs the
data tools into `.venv-data`, not this environment.

See [experiment 0001](experiments/0001-environment.md) for observed results.

## Step 2: bounded data pilot

The historical training dataset is **CommitChronicle**; the later
[CommitBench pilot](experiments/0015-commitbench-pilot.md) stays separate and
was not merged into training. The later 10,000-row expansion was used only by
the separately approved comparison in experiment 0017. See the
[primary-source comparison](research/datasets.md) and
[experiment 0002](experiments/0002-data-pilot.md). The first Windows run selected
1,000 train and 200 validation candidates and retained nine original-source
records for review. The [tokenizer comparison](experiments/0003-tokenizer-comparison.md)
confirmed T5's code/whitespace loss. [Experiment 0004](experiments/0004-learning-set.md)
then reused the manifest, continued verification without another shard download,
and prepared 16 assistant-curated examples using the official CodeT5 tokenizer.

The data tools use a **separate** environment; the CUDA lock is not changed:

```powershell
.\setup-windows.ps1 -Workspace 'D:\PushTrackML' -DataPreparation
& 'D:\PushTrackML\.venv-data\Scripts\python.exe' -m unittest -v `
    test_prepare_pilot test_compare_tokenizers test_continue_pilot

# For an approved first acquisition into a NEW directory only:
& 'D:\PushTrackML\.venv-data\Scripts\python.exe' .\prepare_pilot.py `
    --output 'D:\PushTrackML\data\pilot-0001' --verify-limit 24
```

Run these commands from `ml/` (or the copied Windows `experiment/` directory).
Data dependencies are pinned separately in `requirements-data.in` and
`requirements-data.lock`. The collector refuses existing output, downloads only
two pinned shards plus tokenizer JSON, and never downloads checkpoint weights
or executes repository code. It caps response-body downloads at 400 MB, API
requests at 54 (reserving five remaining requests), and source-verification
attempts at 24. There is no unattended rate-limit retry. All records stay
review-pending, even after automated checks. A nonzero run can still have a
useful report and partial evidence; inspect it before deciding what to do.

Do **not** rerun this command into a fresh directory to continue the existing
pilot: it would repeat selection/downloads, not resume. `continue_pilot.py` was
used for the recorded continuation from the original manifest; its partial
report is preserved at `D:\PushTrackML\data\pilot-0002`. That pass stopped at
the API reserve. The tiny exercise is complete; the later authorized corpus
acquisition below is separate and does not overwrite these pilot records.

Original-diff training rows should follow the contract illustrated by
[example.json](example.json):

| Field | Meaning |
| --- | --- |
| `schema_version` | `1` |
| `repo_id` | Stable repository identity; retained for grouped splitting |
| `commit_id` | Full immutable Git object ID for real commits |
| `source.kind` | `git` for real data; `synthetic` for teaching examples |
| `source.url` | Provenance for real commits; local references may stay private |
| `source.license` | Recorded source-license identifier, with evidence and scope |
| `diff` | Complete unified diff of one selected, coherent commit |
| `message` | Reviewed, single-line English subject; preferably <= 72 characters |

Only `diff` is model input; only `message` is the target. Never leak the commit
subject, commit identifier, or target into the input. Keep multiple files from
one commit together. Real commits need recorded parent selection; exclude
merges initially. Account for additions, deletions, renames, and binary files.
The synthetic example's null provenance is deliberate: it is illustrative,
**not an approved training row or an evaluation set**.

Data requirements for scaling or meaningful quality evaluation (see experiment
0004 for the deliberately narrower evidence of the tiny mechanics set):

- Verify code/message permissions and retain source attribution. A dataset-level
  license does not override the licenses of its component repositories.
- Exclude secrets, credentials, private customer code, generated files, binary
  patches, and meaningless messages. Do not execute source code from samples.
- Deduplicate commits, patches, copied repositories, and forks before splitting.
- Hold out whole repository/fork groups for validation and test, rather than
  randomly splitting rows. Record split identities/hashes and random seeds.
- Count tokens without truncation. Proposed pilot limits are 512 input tokens
  and 64 target tokens; verify them with the chosen tokenizer. Reject/report
  oversized rows rather than silently dropping files/hunks or cutting targets.
- Do not read the test split to tune the model or choose hyperparameters.

A tiny dataset can demonstrate the mechanics but cannot establish production
quality. Training/validation loss alone is not proof of faithful messages.

## Tokenizer-only follow-up (completed)

[Experiment 0003](experiments/0003-tokenizer-comparison.md) compares T5-small,
CodeT5-small, BART-base, and SmolLM2-135M on the existing nine pending examples.
It measures exact encode/decode recovery as well as unknown IDs and token
budgets. CodeT5/BART also lose whitespace around certain literal special-token
strings, so a zero-unknown count alone does not establish fidelity.

The Windows comparison uses the existing data environment, not Transformers or
model weights. To reproduce after approval, use a **new** report directory:

```powershell
& 'D:\PushTrackML\.venv-data\Scripts\python.exe' -m unittest -v `
    test_compare_tokenizers test_prepare_pilot
& 'D:\PushTrackML\.venv-data\Scripts\python.exe' .\compare_tokenizers.py `
    --pilot 'D:\PushTrackML\data\pilot-0001' `
    --output 'D:\PushTrackML\runs\tokenizer-new'
```

Only allowlisted tokenizer/card/config files (under a 6 MB response-body cap)
are fetched; the corpus and review status are read-only. The successful report
is already at `D:\PushTrackML\runs\tokenizer-0002\report.json`. CodeT5-small is
the smallest technical candidate; its license wording remains unresolved for
product distribution. SmolLM2-135M is a larger Apache-2.0-documented fallback.
See the experiment for reference-backend caveats and the required next gates.
This comparison is not a trained-model quality, speed, or RAM benchmark.

## Step 3: first learning exercise (completed)

The small set is at `D:\PushTrackML\data\pilot-0002\learning-set\`.
It contains 11 training and five project-separated validation examples, with
three multi-file commits. Seven original subjects were retained; nine were
explicitly rewritten by the coding assistant from the diffs. Every replacement
retains its original subject and review rationale. This is not independent
human annotation, and it is below the original 20-50-example target.

[Experiment 0005](experiments/0005-first-training.md) downloaded the pinned
approximately 242 MB checkpoint, loaded it safely, and fine-tuned all 60,492,288
parameters for exactly 100 updates. Training loss fell from 9.5279 to 0.2561;
validation loss increased from 8.2191 to 8.9897. Exact subjects: 8/11 training,
0/5 validation. Validation examples received no updates. These results prove
the mechanics, not useful generalization.

Training uses `.venv-train`, created by `setup-windows.ps1 -Training`, with
`requirements-train.lock`; neither earlier environment is changed. The saved
safetensors checkpoint at `D:\PushTrackML\runs\training-0001\checkpoint` was
reloaded offline and reproduced the recorded outputs. Eight training tests and
35 data/tokenizer tests passed. See experiment 0005 for the fixed recipe,
reproduction commands, artifact hashes, and failure examples.

Do not rerun or expand training automatically. Compression, broad evaluation,
and PushTrack integration remain deferred. Dataset limitations remain in
[experiment 0004](experiments/0004-learning-set.md).

## Step 4: corpus-scale data preparation (audited; readiness gates remain)

The user authorized the full train/validation acquisition: 73 pinned Parquet
shards totaling 12.21 GB, with 7,659,458 training and 1,554,042 validation records.
The 1,486,267-record test split remains untouched. Existing pilot shards are
reused; processing stays on Windows and streams into a disk-backed SQLite index.

`download_corpus.py` completed hash-verified acquisition. `prepare_corpus.py`
scanned all rows and exported **743,787 training / 133,228 validation candidates**
across 4,708 / 589 repositories, with zero case-insensitive repository overlap.
Export hashes and exact row accounting passed the offline audit. There is no
first-500-row limit. Artifacts are at `D:\PushTrackML\data\corpus-0001`; see
[experiment 0006](experiments/0006-corpus-preparation.md).

`verify_corpus_sources.py` completed batched public Git reconstruction of
**10,000 train + 1,000 validation** examples across 185 + 59 repositories. It
preserved old/new source snapshots and recognized MIT notices rather than
assuming processed dataset modifications were complete. See
[experiment 0007](experiments/0007-original-source-checks.md).

`audit_corpus.py` independently verified all 11,000 records, including byte-exact
patch application, Git/source identities, provenance, and lossless token budgets.
**61 Windows regression tests passed.** Quality screens, prior holds, and a new
24-example assistant review leave **9,758 train + 962 validation candidates**.
All 280 held examples remain traceable; subjects were not silently rewritten.
Only 40 distinct records have received assistant semantic review, not independent
human annotation. Canonical/fork metadata was checked for 51/244 repositories
before stopping at the anonymous API reserve; 193 identities remain unresolved.

Final pending files are in
`D:\PushTrackML\data\corpus-0001\audit-0002\post-review-pending`. Historical
quality-approval flags remain false; the later explicit authorization for a
bounded research run is recorded separately in
[experiment 0009](experiments/0009-corpus-training.md). See
[experiment 0008](experiments/0008-corpus-audit.md) for the immutable audit evidence.
Do not rerun collection or the full integrity audit to continue metadata checks.

Published `processed_mods` are not guaranteed full original diffs. The large
candidate-index exports are not training inputs; only the smaller reconstructed,
filtered original-source exports are used by the new hash-locked `train_corpus.py`.
The old tiny trainer still accepts only its original 11/5 learning set.

## Fixed CommitBench research comparison (completed)

[Experiment 0017](experiments/0017-commitbench-training.md) records the completed
three-epoch comparison on all 10,000 new source-checked rows, not a merger with
the historical corpus or 117-row pilot. `train_corpus.py` keeps `chronicle-frozen`
as its historical default; `--data-version commitbench-source-0002` pins the exact
pending export, manifest and separate source/quality evidence. The completed
recipe used `--epochs 3`; the later explicitly requested `--epochs 100` run is
recorded separately in [experiment 0018](experiments/0018-commitbench-hundred-epochs.md).
No arbitrary epoch counts are allowed. It retains every official token/identity/
split gate and rejects changed flags. Permission is recorded separately, not in immutable data flags.

The existing `.venv-train` and original weights were reused. Forty-six focused
native tests passed, including the alternate loader and unchanged historical
trainer/decoder tests. New runs require separate authorization; never overwrite
`runs\training-0005` or automatically extend because training loss decreases.
The predeclared final epoch remains selected even though epoch 2 has lower
validation loss. Loss/lexical overlap and the reused semantic sample do not
establish a reliable product model.

## Model candidates and license scope

Cards reviewed on 2026-10-03:

- [google-t5/t5-small](https://huggingface.co/google-t5/t5-small): approximately
  60M parameters; Apache-2.0 metadata. An accessible text-to-text baseline, not
  code-specialized. Pretraining includes C4 and other tasks; downstream quality
  for Git diffs must be measured. Only its pinned tokenizer JSON was used in
  experiment 0002; observed `<unk>` tokens are a suitability concern, not a
  reason to change the tokenizer independently of the pretrained weights.
- [Salesforce/codet5-small](https://huggingface.co/Salesforce/codet5-small): a
  code-specialized encoder-decoder candidate with a code BPE tokenizer. Its
  card lists Apache-2.0 but also says the release is for research purposes only
  and references Salesforce AUPs. Resolve this wording and the applicable
  weight/license terms before choosing it for distribution. It is not already
  a commit-message model.
- [bigcode/commitpackft](https://huggingface.co/datasets/bigcode/commitpackft):
  dataset metadata says MIT, but rows have separate source-repository licenses,
  including `unknown` and copyleft identifiers. It contains before/after file
  contents rather than ready-made complete commit diffs. Do not assume a row
  covers an entire multi-file commit; check the upstream filtering/construction
  code before using it. It has not been downloaded or approved as training data.

CodeT5-small's pinned weights were downloaded after explicit approval and used
for the completed research runs in experiments 0005, 0009, 0011, 0013, and 0017,
and reused again for the user-stopped experiment 0018. Later runs reuse original
weights without another download. Product-distribution
licensing remains unresolved. Do not run remote model code or replace the pretrained
vocabulary. Further training beyond the approved recipe or product integration
requires a separate decision.

## Later milestones and release gates

1. **Environment:** dependency lock and actual GPU forward/backward proof.
2. **Data:** provenance, quality filters, grouped held-out splits, token-length
   statistics, and manual review of a small pilot.
3. **Training:** reproduce an unfine-tuned baseline, overfit a tiny diagnostic
   subset, then train the pilot. Record seeds, hyperparameters, checkpoints,
   train/validation losses, and rejected examples. No quality claim from overfit.
4. **Evaluation:** compare against the baseline and a simple deterministic
   summary. Review faithfulness, useful specificity, invented claims, English,
   multi-file coverage, and subject length on untouched held-out repositories.
   Exact string match is not enough: multiple messages can be correct.
5. **Deployment:** investigate ONNX/INT8 only after useful quality is measured.
   Compare compressed quality against the uncompressed model. Record total
   artifact size (all graphs/tokenizer/runtime), cold-start latency, p50/p95
   latency, and peak **process RAM** on declared CPU hardware and input sizes.
   GPU allocator memory is not process RAM. Roughly 60M INT8 parameters implies
   about 60 MB of weights only, not a measured runtime or distributable size.
6. **Integration:** only if CPU memory/latency and quality meet declared budgets.
   Keep folder configuration and monitoring unchanged; require preview and
   confirmation for any future commit/push feature.

A CV may describe the reproducible 60M-parameter fine-tuning pipeline, 9,758
source-checked training examples, and the measured validation-loss improvement
in experiment 0009, with the documented split/label limitations. Reliable
semantic quality, compression, CPU RAM savings, and a publish feature remain
unproven; do not claim them.

## Repository hygiene

Keep raw/processed datasets in `ml/data/`, checkpoints in `ml/checkpoints/`,
exports in `ml/exports/`, and runtime reports in `ml/runs/`, or outside the repo
in the dedicated workspace. These directories, caches, and virtual environments
are ignored. Commit only code, small synthetic fixtures, dependency locks, and
sanitized evidence notes. Never commit SSH keys, credentials, model weights, or
real/private sample diffs. Do not sync the entire workspace back from Windows.
