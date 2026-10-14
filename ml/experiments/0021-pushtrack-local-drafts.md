# Experiment 0021: on-demand editable PushTrack drafts

Date: **2026-10-13**. User explicitly approved integration with `evet ekle`.
Work was performed inline; no subagents or agent/model switching.

## Product slice

The Rust dashboard now has an experimental **`m`** action for the selected
repository. Supply `--ai-model`, `--ai-server` and optionally `--ai-python` with
`--watch`. Model/runtime paths are not persisted, downloaded or bundled.

**Scope is explicitly the entire staged index, not all uncommitted work.**
PushTrack never stages, commits, pushes or modifies the selected repository.
The modal shows the scope, selected path and file count. Type/Backspace edits
at the end; Ctrl+U replaces the subject. Enter performs another staged-diff /
HEAD / branch check and marks it reviewed without committing. Copy manually;
Esc discards/closes or cancels, Ctrl+C exits. This is a point-in-time check,
not an atomic lock on external Git operations or a semantic truth certificate.

### Ownership and reuse

- `src/draft.rs`: staged-diff capture, complete-file accounting, local runtime
  setup, single owned background job and revalidation.
- `src/process.rs`: extraction of the existing file-backed, timeout/cancellable
  Unix process-group lifecycle. Git retains its interface and20s timeout.
  Bounded draft output and whole-group cleanup also cover model failures/exits.
- `src/ui/draft.rs`, `src/ui/{mod,terminal,render}.rs`: scoped modal editing,
  independent job polling, reviewed/error states, safe rendering and cancellation.
- `src/cli.rs`: paired optional local-asset flags requiring watch mode.
- Reuses the verified `ml/local_subject.py` as an **embedded standard-library
  connector**, rather than introducing HTTP/provider libraries or an installed
  helper dependency. Source SHA remains
  `3cb04d49f2002cd7e7732d82dfe18e8ac84b0e48f8ad62097ddab20870164f3e`.

No Cargo dependencies or model prompts/weights changed. Model inference is
isolated Python (`-I -S -X utf8`), explicitly CPU-only with two threads,192
output tokens,4096 context, no tools/agents/cache/context shifting/downloads.
Temporary script/input/logs belong to the Rust-owned temporary directory,
including cancellation cleanup. No model is run during scans or refreshes.

### Collection/safety boundaries

Read-only cached diff plumbing avoids applying source clean/textconv/external
diff filters. Optional index writes, fsmonitor and lazy object downloads are
disabled. Complete raw metadata, numstat and patch file counts must match.
Capture is repeated and checked for stable branch/HEAD and staged content before
generation, after generation, and again on Enter.

- Explicitly rejects conflicts, binary/mixed-binary diffs, symlinks, gitlinks,
  unsafe filename controls, invalid UTF-8 and excessive bytes.
- Entire staged patch up to262,144bytes; context overflow remains a strict
  tokenizer refusal in the verified connector. No omitted files/hunks or
  shortened model output are accepted.
- Rename detection disabled: moves are represented as complete removal/addition.
- Runtime version must identify **llama.cpp commit d81235049 / b11429**, clean
  build; exact model hash is checked by the connector before loading.
- Single-line subjects at most72characters; controls, bidi formatting and
  unexpected extra output are rejected, not sanitized into an accepted title.
- Esc/quit/signal cancels the owned job and its process group, including C++
  descendants. Unexpected connector exit also kills remaining owned helpers.

## Actual verification

**Baseline26Rust tests passed** before process extraction; the same26passed
immediately after that ownership move. New focused integration tests cover
complete multi-file staged additions/modifications/deletions, unborn HEAD,
no changes, untouched index/HEAD, not including unstaged/untracked content,
binary/oversized/encoding/filename/mode/conflict rejection, disabled diff drivers,
actual stdin bridge bytes, format refusal, post-generation races, Enter rechecks,
wrong-runtime refusal, cancellation, exited-parent descendants and output bounds.
UI tests cover editing, limits, scoped keys and supported-size modal rendering.

Final gates passed: **42 Rust tests** (six suites,2.74s), `cargo fmt --all --check`,
`cargo clippy --all-targets --locked -- -D warnings`, release build and the full
PTY acceptance suite. No training or research-data tests were rerun under a claim
of application coverage.

The real PTY suite (`scripts/test_tui.py`) exercises the release binary:
existing navigation/resize/fetch/signal restoration still pass, plus **m only on
request**, staged-only diff capture, editing, Enter review, stale-index refusal,
Esc cancellation and killed model descendants. These application tests use
**explicit synthetic repositories and fake inference transport on macOS**.
They do not establish actual model behavior on macOS/Linux.

### Native real-model bridge and resource observation

The PTY test exported the **actual Rust-collected synthetic patch** and
**actual embedded connector bytes**. They were sent to the user's Windows ML
machine and invoked with the identical isolated Python flags and verified
GGUF/runtime. All real inference remained **native Windows**.

Evidence: `D:\PushTrackML\runs\app-local-draft-0001\report.json` — **passed**.

- Diff SHA-256: `da066cededed69e83395f78aef7a985f32a9945a6f91a8e31099564c28e4aee7`.
- Model SHA-256 unchanged:
  `00fe7986ff5f6b463e62455821146049db6f9313603938a70800d1fb69ef11a4`.
- Returned grounded synthetic subject: `Add TIMEOUT constant to constant.py`.
- Exit0, **132 prior protected artifacts unchanged**, runtime files verified.
- **19.328s** connector wall time including hash/startup/generation for that
  **one small staged addition**, not a latency distribution/cold-disk benchmark.
-200ms process-tree sampling: **4,552,601,600bytes** maximum aggregate working set
  (~4.55GB/~4.24GiB), C++ individual observed peak4,522,450,944bytes.
  Excludes RustUI peak and file-cache residency; shared pages can be counted
  in more than one process. This is **not** Mac/Linux resource proof.
- Final observation: **zero remaining owned Python/server workers**, no training
  restart. Separate runtime metadata inspection reported b11429/d81235049.

The complete Unix RustUI + real model deployment remains **unverified** due to
the native-Windows research constraint. The model and runtime need explicit local
setup on the target platform; do not run the Windows executable on macOS/Linux.
No Windows support was added to the Unix-specific Rust dashboard.

## Preservation and stop

The [selected-model development gate](0020-verified-local-draft-model.md) remains
limited reused evidence:18usable/2needs-edit in20cases,12faithful synthetic core
changes, seven interpretation-sensitive judgments. No population accuracy or
production quality guarantee; edited drafts still require user review.

No optimizer updates, dataset/target/approval changes, automatic downloads,
commits/pushes or new authentication were performed. The100-epoch run remains
user-stopped after71measured epochs; checkpoints and all prior evidence remain.
No automatic research restarts are scheduled. This completes the requested
narrow integration; clipboard/editor/commit actions and new providers are not added.
