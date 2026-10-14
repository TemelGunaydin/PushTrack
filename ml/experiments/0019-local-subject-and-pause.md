# Experiment 0019: local subject prototype and user-requested pause

Date: **2026-10-12**. Work is **stopped**, not automatically resuming tomorrow.
No production model was accepted and no Rust message-generation feature was added.

## Product outcome and bounded gate

The user's goal is a local model producing short English commit-message drafts
from complete selected changes in PushTrack. No source uploads, paid inference,
unattended commits or pushes. Suggestions remain editable and require review.

The declared development gate is at least **18/20 usable** reused subjects,
zero central unsupported/contradicted actions, and faithful handling of all
**12 synthetic critical cases**, including source-comment instruction injection.
These are repeatedly reused, unblinded development judgments and assistant-authored
fixtures, not independent population accuracy or gold labels. No test split,
optimizer updates, target rewrites, or proposal applications occurred.

## Completed CPU prototype trials

Verified official **Qwen2.5-Coder-1.5B-Instruct Q4_K_M**, Apache-2.0:

- Revision `f86cb2c1fa58255f8052cc32aeede1b7482d4361`.
- File `qwen2.5-coder-1.5b-instruct-q4_k_m.gguf`, **1,117,320,768 bytes**.
- SHA-256 `cc324af070c2ecbfd324a30884d2f951a7ff756aba85cb811a6ec436933bb046`.
- Model directory: `D:\PushTrackML\checkpoints\qwen-coder-1.5b-gguf-0001\`.

Verified official MIT **llama.cpp b11429 CPU-x64** runtime:

- Revision `d81235049384534c167caea52b85a694f6103d14`.
- Archive `llama-b11429-bin-win-cpu-x64.zip`, **19,398,918 bytes**.
- SHA-256 `1283323272b04cd07905816a597a0da810918102de958f4ff6f7bbaa70ed2efe`.
- Runtime: `D:\PushTrackML\runtimes\llama-b11429-cpu-0001\`.
- Acquisition evidence: `runs\local-model-acquisition-0001\report.json`.

All actual inference ran natively on Windows with **two CPU threads**, zero GPU
layers/offload, loopback-only HTTP and no tools/agents/UI. Requests retained the
complete original diff, checked tokenizer roundtrips, reserved a **4096-token**
context with **96 output tokens**, and rejected truncation/control markers.
Output was a strict JSON subject, at most 72 characters; owned server processes
were closed afterward. This is functional evidence, not latency/RAM profiling.

Repository prototype: `ml/local_subject.py`, `ml/test_local_subject.py`.
**11 synthetic contract tests passed natively** after the literal edit audit
was added; earlier nine-test variants also passed. No Rust application tests
were rerun or claimed for these ML-only changes.

Three same-case, same-weight trials are preserved:

- `runs\local-subject-0001\`: first prompt; review **7 usable / 6 needs-edit /
  7 misleading**, **9/12** critical cases faithful. Explicitly rejected.
- `runs\local-subject-0002\`: diff-role-aware prompt; still confuses context,
  TODOs, guards and units, and one format failure. Explicitly rejected.
- `runs\local-subject-0003\`: full diff plus deterministic removed/added lines
  and minimal textual edits. This improved some scoping but still produced
  duplicate-proTx claims, comment-as-behavior claims, malformed identifiers,
  guard-as-whitespace descriptions and invented units. **Does not meet the gate**;
  a separate formal review file is not yet written. Do not integrate/promote it.

The edit audit is literal derived input, not an AST or semantic verdict. Original
full diffs remain in the prompt; labels/subjects/IDs are not used as model inputs.
Original evidence and corpus flags remain unchanged; benchmark source data retain
their noncommercial research restrictions. The pretrained weights were not trained
on the research records during these trials.

## Next candidate: download interrupted, not verified

The official `Qwen/Qwen3-4B-Instruct-2507` is a non-thinking Apache-2.0 model.
An assumed official GGUF repository returned **HTTP 401**; it was abandoned,
not retried or bypassed with credentials. Primary repository evidence instead
lists official Safetensors and a separately published Unsloth quantization.

Pinned **Unsloth**, not official Qwen, Q4_K_M:

- Repository `unsloth/Qwen3-4B-Instruct-2507-GGUF`.
- Revision `a06e946bb6b655725eafa393f4a9745d460374c9`.
- Official base revision `cdbee75f17c01a7cc42f958dc650907174af0554`.
- File `Qwen3-4B-Instruct-2507-Q4_K_M.gguf`, **2,497,281,120 bytes**.
- Expected SHA-256 `3605803b982cb64aead44f6c1b2ae36e3acdb41d8e46c8a94c6533bc4c67e597`.
- Metadata/license: `experiment\local-model-research-0003\`.
- Acquisition evidence: `runs\local-model-acquisition-0002\`.
- Partial file: `checkpoints\qwen3-4b-gguf-0001\Qwen3-4B-Instruct-2507-Q4_K_M.gguf.part`.

At stop, **2,401,239,040 bytes** were retained in `.part`. It is **not a verified
model** and must not be loaded/promoted. No Qwen3 inference occurred. Reuse the
verified existing runtime only after a deliberate, preservation-safe acquisition
continuation; do not blindly rerun the overwrite-protected downloader or redownload.
The roughly 2.50GB size is an unresolved deployment tradeoff, not proof of suitability.

## Stop and tomorrow's continuation

At **20:32:38 UTC**, the exact verified parent process trees **22076** (trainer)
and **8392** (download) were stopped. **Zero owned model/download Python or
llama-server workers remained**, the native sleep controller exited, and no
Mac training/caffeinate controller was observed active. No files were deleted.
Native evidence: `D:\PushTrackML\runs\user-pause-0001\`.

[The 100-epoch run](0018-commitbench-hundred-epochs.md) stopped during epoch 72,
with **71 measured epochs/checkpoint directories**, last reported **88,850
updates / 710,800 exposures**. Completion verification remains pending. Saved
model/tokenizer checkpoints do **not** include optimizer resume state; exact
optimizer/step continuation must not be promised or performed automatically.

When the user resumes work:

1. Reobserve owned processes and preserved pause/artifact evidence; do not launch
   overlapping work or overwrite old execution/report directories.
2. Continue toward the actual product goal, preferably assess the pinned stronger
   CPU candidate on the **unchanged 32 cases** after verified acquisition.
3. Preserve rejected outputs and record the missing third-trial review separately.
   Do not weaken the gate or claim blind accuracy from repeated development cases.
4. Integrate only a suitable candidate via existing Git/UI seams, on demand,
   complete-input/context-safe, editable, with no Git writes. Windows research
   does not add Windows support to the Unix-specific Rust application.
5. Keep the interrupted hundred-epoch work separate. Decide a traceable resume
   recipe only with user direction; never infer a complete 100-epoch proof.

No commit or push was performed. CPU latency/RAM, oversized/unsupported real-diff
handling, cross-platform runtime packaging and end-to-end app usability remain
unproved. The repository remains modified `.gitignore`/`README.md`, untracked `ml/`.
