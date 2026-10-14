# Experiment 0020: verified local editable-draft model

Date: **2026-10-13**. The user resumed work with `devam et`. The requested
**obtain a useful local model** milestone is reached for an **editable-draft
prototype**, not a production-quality guarantee. Rust dashboard integration
has **not** been implemented.

## Selected artifact

**Qwen3.5-4B Q4_K_M**, published as a **third-party Unsloth quantization**, not
an official Qwen GGUF:

- Base: `Qwen/Qwen3.5-4B`, revision `851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a`.
- Quantization: `unsloth/Qwen3.5-4B-GGUF`, revision `e87f176479d0855a907a41277aca2f8ee7a09523`.
- File: `Qwen3.5-4B-Q4_K_M.gguf`, **2,740,937,888 bytes** (approximately 2.74GB).
- SHA-256: `00fe7986ff5f6b463e62455821146049db6f9313603938a70800d1fb69ef11a4`.
- License: **Apache-2.0**; pinned base license/README and quantization attribution retained.
- Native artifact: `D:\PushTrackML\checkpoints\qwen35-4b-gguf-0001\`.
- Acquisition: `runs\local-model-acquisition-0004\report.json`, verified one
  transfer, **zero retries**, **23 protected artifacts unchanged**.

Existing verified **llama.cpp b11429**, revision
`d81235049384534c167caea52b85a694f6103d14`, **MIT** Windows CPU-x64 runtime
was reused. Its pinned architecture table supports Qwen3.5. No new runtime,
packages, multimodal projection, GPU inference or optimizer updates were used.
License notices must accompany future redistribution; no model was bundled or
published in Git. Benchmark source data retain their separate research terms.

Machine-portable asset/policy metadata: [`../local-model.json`](../local-model.json).

## What was actually evaluated

Same **20 repeatedly reused development diffs** and **12 predeclared synthetic
critical cases**, no replacements. Complete original diff and literal
removed/added hunk lines enter the model. The audit is not an AST or semantic
verdict; reference subjects, labels, IDs and source review metadata are not inputs.

- Windows native CPU, **two threads**, GPU layers/offload **zero**.
- Localhost-only ephemeral server; no paid/remote inference, tools, agents or UI.
- Jinja template, reasoning explicitly **off**.
- **4096** context tokens, **192** output-token reservation, deterministic
  greedy decoding/seed42, no prompt cache or context shifting.
- Internal `edit_summary` (maximum300 characters), then subject (maximum72).
  Internal analysis is not a truth certificate and is not shown by the connector.
- Complete-diff template preservation, tokenizer roundtrip, prompt token
  accounting and non-truncated output checked. Oversized input is refused,
  not shortened or missing changed files.

Frozen run: `D:\PushTrackML\runs\local-subject-0010\`.
Frozen policy source SHA-256:
`d1934c4ac773ce34b9cd1ea0bb4c71f178c038b623891fc327ade4c56975c037`.
Identical case-file SHA-256 across trials:
`07b423a31d6e816ca4247a453fcc6602267add2c01a47bdea13122b8eac82890`.

### Manual development result

**18 usable / 2 need editing / 0 centrally misleading** in those 20 cases.
**12/12 synthetic core changes faithful**, including comment-only edits,
existing dependencies/classes/holidays, guard removal, blacklist direction,
multiple projects, file add/delete/rename, and instruction-like source comments.

**Seven judgments are interpretation-sensitive.** In particular, duplicate
proTx *for the same operator key* is accepted as shorthand for key-sharing
conflicts, not the earlier wrong duplicate-hash claim. Two drafts need correction:
unsigned-literal rationale/terminology and namespace-type versus runtime-constant
terminology. Repeated development judgments are **not 90% population accuracy**,
independent human gold, a blind final test, exhaustive coverage or perfect
faithfulness. User editing/review remains necessary. No corpus approval flags
or targets changed, and thirteen historical proposals remain unapplied.

### Fresh reload and safety proof

`runs\local-subject-proof-0001\report.json` **passed**, 13:49:23–13:51:26UTC:

- All32 input identities, exact complete-diff inclusion, token budgets and
  output-format/EOS/non-truncation mechanically verified.
- Fresh reload reproduced **six predeclared hard cases** with exact input
  token IDs, output token IDs, raw content and subjects.
- Oversized synthetic input rejected **before any completion request**.
- Model-control-marker input rejected; owned server exited.
- **132 protected artifacts** and selected weights/runtime remained unchanged.

This proves mechanics/reproducibility, not independent semantic correctness.
CPU latency and process-RAM profiling were not performed.

## Usable standalone connector

[`../local_subject.py`](../local_subject.py) now accepts a complete selected
UTF-8 unified text diff on stdin and prints only one English subject. Requires
**Python3.11+**, the exact pinned model, and a trusted local b11429 CPU server.
No inference packages, downloads, model-provider abstraction, Git commands,
commits, pushes or saved server are added. Model size/hash is checked before
loading. Model memory is released when its owned server exits.

Example with the already verified native synthetic patch (PowerShell invokes
`cmd` to keep the pipe binary rather than normalize source text):

```powershell
cmd /d /c "type D:\PushTrackML\runs\local-subject-cli-proof-0001\diff.patch | D:\PushTrackML\.venv-data\Scripts\python.exe D:\PushTrackML\experiment\local_subject.py --model D:\PushTrackML\checkpoints\qwen35-4b-gguf-0001\Qwen3.5-4B-Q4_K_M.gguf --server D:\PushTrackML\runtimes\llama-b11429-cpu-0001\bin\llama-server.exe"
```

A user-selected staged **text** diff can similarly be supplied from
`git diff --cached --no-ext-diff --no-textconv --no-color`; this selects only
staged changes and does not include unstaged/untracked work. The connector itself
does not collect, stage, edit or commit files. Binary/combined/submodule/conflict
handling and repository mutation detection require a future application collector;
do not claim those are covered by this prototype.

**18 native contract tests passed** (0.085s), including input/output validation,
wrong model size/hash, context refusal, exact boundary whitespace, stdin caps,
invalid UTF-8 and owned-process cleanup. No Rust tests were rerun or claimed.

`runs\local-subject-cli-proof-0001\report.json` **passed** with the real selected
GGUF through stdin: exact synthetic subject on stdout, exit0, verified inference
policy unchanged, **133 prior artifacts unchanged**, no remaining owned workers.
Connector source SHA-256:
`3cb04d49f2002cd7e7732d82dfe18e8ac84b0e48f8ad62097ddab20870164f3e`.

A proof-helper preflight initially failed with `TypeError: ... LocalCPU ...
built-in class`: dynamically loaded modules were missing from `sys.modules`
for class source inspection. No model inference or proof output had started.
Failed helper/evidence retained in `runs\local-subject-cli-preflight-0001\`;
registering the modules corrected the helper, not model/application behavior.
The completed writer was not blindly rerun.

## Preserved alternatives and diagnosed failure

The previously paused Qwen3 download was completed into a **new directory** using
one validated **206 Range** request for only **96,042,080** remaining bytes.
Full file size/hash passed; original **2,401,239,040-byte** prefix and16 prior
artifacts remained unchanged (`runs\local-model-acquisition-0003\`).

Qwen3-4B policies `local-subject-0004` through`0007` were rejected: first
16usable, refined17usable with one misleading file-addition claim, then repeated
context/terminology/instruction-echo mistakes. No threshold was relaxed. Their
weights, cases, outputs and separate reviews remain preserved.

Qwen3.5 first attempt `local-subject-0008` stopped **before generation** because
its native Jinja template trimmed the user message's final diff newline.
`local-template-diagnostic-0001` proved zero exact full-diff occurrences in raw
rendering and exactly one after interior framing, with **zero completions**.
The fix preserves every original diff byte; it does not silently strip input.
`local-subject-0009` then completed but still failed key/hash/comment-scope gates.
The final`0010` policy supplies literal line roles without noisy character edits.
All failed/rejected evidence remains separate; nothing was overwritten.

## Stop condition and remaining product work

The **useful local-model prototype milestone is complete**. No automatic further
training/downloads are scheduled. The [100-epoch research run](0018-commitbench-hundred-epochs.md)
remains user-stopped after71 measured epochs; no optimizer-state resumption or
100-epoch completion is claimed. Its checkpoint71 and pause evidence remain intact.

**PushTrack's Rust dashboard still has no AI action.** Next product work requires
an explicit local asset/runtime setup and packaging decision: 2.74GB is a material
tradeoff. Add on-demand editable drafts via existing Git/UI seams, with complete
selected-change collection, unsupported-input refusal, repository race detection,
owned-process cancellation and no unattended Git writes. Measure deployment
CPU/RAM and exercise the application path separately; Windows model research
does not add Windows support to the Unix-specific Rust dashboard.

No commits or pushes were performed. Datasets/models/reviews remain outside Git.
