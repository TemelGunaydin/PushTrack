# 0024 — Actual Mac ARM64 dashboard CPU drafts

## Scope and result (2026-10-13)

The user separately approved **actual Mac inference**, departing the earlier
Windows-only inference boundary, then explicitly approved runtime acquisition
and installation after target inspection. Dataset processing/training was not
moved to Mac; **the hundred-epoch run remains stopped**, with71measured epochs.

**Passed** actual release-binary TUI + pinned model/runtime proof on a synthetic
repository: generation, editable subject, Enter review without Git writes,
Enter refusal after a fixture-controlled staged-index change, Esc cancellation
and Ctrl+C exit while a real C++ model server was resident, process-tree cleanup
and terminal restoration. No product code changes were needed for this proof.
No source uploads, paid API, Git commit/push, unattended daemon, optimizer updates,
system/PATH/security changes or model-policy/quality promotion occurred.

Subject: **`Add TIMEOUT constant to constant.py`**, generated twice from the same
small diff. This names the actual staged `TIMEOUT = 10` addition; it is a reused
simple synthetic example, **not a new semantic validation corpus, independent
human annotation, population accuracy or a production promotion**.

## Target and installation

- macOS27.0.1 / Darwinarm64;64GiB RAM,16physical/logical cores;27GiB free at inspection.
- Existing Python3.12.13 used explicitly; Python3.14.6 was also available.
- No compatible scoped installed `llama-server` was found; existing GGUF exact
  size/SHA verified. No new model download/default-cache move.
- User-approved official runtime archive:
  https://github.com/ggml-org/llama.cpp/releases/download/b11429/llama-b11429-bin-macos-arm64.tar.gz
- Archive bytes11971406, SHA-256
  740288ec6887be94280a5dfa25b5e23a78285cab104519e6c7e218904ee82459.
- Release target:d81235049384534c167caea52b85a694f6103d14.
- One bounded public HTTPS download, retries0. Before extraction: size/hash,
  member types, no absolute/traversal paths, bounded unpacked bytes, safe in-root
  non-cyclic/dangling relative library links, no hardlinks/devices. Python data
  extraction filter used. MIT LICENSE matched pinned native license hash
  94f29bbed6a22c35b992c5c6ebf0e7c92f13b836b90f36f461c9cf2f0f1d010d.
- Installed only into a new user cache:
  `~/.cache/pushtrack/runtimes/llama-b11429-macos-arm64-0001/llama-b11429/`.
  No sudo, PATH modification, quarantine/security bypass, global package change,
  replacement of prior assets or runtime source build.

Actual version:

```text
version: 0.6.0-dev (build 11429, commit d81235049)
built with AppleClang 21.0.0.21000101 for Darwin arm64
```

Official package contains a Metal backend, but **execution explicitly disables
GPU selection/layers, KV/op offload**. Captured owned server argv establishes
`--device none --n-gpu-layers 0 --no-kv-offload --no-op-offload`, two compute/batch
threads, one HTTP/parallel slot, ctx4096, fit off, no context shifting/model
autoload/agents/UI/MM projection. Model, prompt/output policy, standard-library
connector and input/refusal contract unchanged (4096context/192output; full
staged input, no omitted hunks, raw/token/template preservation and EOS checks).

## Actual TUI proof

Location: `~/.cache/pushtrack-dev-evidence/mac-native-draft-0001/`.
Runtime archive/install hashes, version, executed helpers and all failed/corrected
attempts preserved. **Completed proof:** `tui-proof-0002/proof-report.json`,
2026-10-13T19:41:37.117669+00:00 to19:42:18.234136+00:00.

A freshly initialized synthetic repository (unborn HEAD) has staged constant.py,
plus an explicitly untracked synthetic file. The fixture driver alone uses
`git init/add`; PushTrack performs no repository writes. Index bytes and symbolic
HEAD remain equal before/after generation/edit/Enter, and equal to the fixture's
new staged snapshot after stale refusal/cancellation/exit. Untracked data is not
in the selected staged diff. Input patch SHA-256:
da066cededed69e83395f78aef7a985f32a9945a6f91a8e31099564c28e4aee7.

1. Press `m`; actual server/model returns the35-character English subject above.
   Ctrl+U edits; Enter rechecks and shows Reviewed subject. No index/HEAD change.
   Successful completion leaves no owned Python/C++/Git descendant.
2. Close; generate again from the same complete staged diff (same subject).
   Fixture changes/stages TIMEOUT10→11, then Enter refuses stale snapshot and
   clears the subject. No app modification of the fixture's new index.
3. Start an actual model job; wait until C++ sampled RSS>=1GiB (not merely Python
   hashing). Esc closes in0.059s in this observation; owned descendants gone,
   lock-free responsive dashboard, q exits/restores terminal.
4. A new dashboard starts an actual resident model job. Ctrl+C exits130, restores
   alternate screen/cursor/raw/echo state and leaves no owned tree alive.

The existing real PTY Session driver was reused without importing/executing its
unrelated test fixtures. Only runtime/model/user-private cache paths were passed;
no default folder settings changed and no model run during scans.

### Bounded resource observation

The first completed `m` request took **17.7736s** to an editable subject, including
Rust staged collection/runtime-version check, model hash, CPU startup, generation
and UI observation. Repeated/previous checks had warmed filesystem cache. This is
**not a cold-disk benchmark, latency distribution or isolated connector timing**.

`ps`-based owned process-tree RSS sampling:0.2s requested pauses plus command/log
sampling overhead;69samples for the first completed case. Maximum aggregate RSS
**5991563264bytes (~5.99GB /5.58GiB)** for Rust + owned Python/C++/Git processes.
Sampled per-process peaks: Rust5013504, Python27836416, llama-server5958746112bytes.
Separate peaks need not occur simultaneously. Shared pages can be counted more
than once; OS file-cache residency/proof-helper memory is not included. RSS differs
from Windows working-set metrics, so this does **not** prove comparative speed/RAM
or resource suitability for other hardware/diffs. Allow headroom and measure.

## Failures and diagnostic limits retained

- `tui-proof-0001` reached the actual faithful subject but **failed the test helper's
  extraction**: first/last vertical borders included nested dashboard/modal borders
  and made a >72-character string. Saved failure screen proves intact output.
  Product code was not changed. Corrected helper uses subject-box coordinates and
  the UI character count; a new `tui-proof-0002` completed all conditions.
- An extra final-integrity helper initially required live argv for every completed
  case. The sampling helper's final-snapshot update replaced the first completed
  case's live argv with `<defunct>`. That failed assertion/helper is preserved;
  **no live snapshot was fabricated**. Corrected, separate integrity report verifies
  unchanged embedded connector in all four completed cases and four retained live
  CPU argv records across attempts (initial001generation, completed002second
  generation/Esc/Ctrl+C). The first completed case's final live-argv detail is
  unavailable; its unchanged connector, owned server/RSS and startup logs remain.
- No completed proof writer was overwritten or rerun into the same output path.

Final integrity: `final-integrity-report-0002.json`, passed at
2026-10-13T19:45:05.926478+00:00: all installed runtime files/links unchanged,
original GGUF size/hash unchanged, current binary/connector match completed proof,
actual retained CPU flags validated. Embedded connector SHA:
3cb04d49f2002cd7e7732d82dfe18e8ac84b0e48f8ad62097ddab20870164f3e.
Release binary SHA:
cb4416334771e53ec319c3cbee11aa5353e0434a3a2753f3be249fb3ca524f1f.

Still-current source gates:52Rust tests (3.09s), fmt, strict Clippy and release build
passed immediately before this proof. No product source changed afterward; only
verification/documentation metadata. No claim of research/training tests as TUI
coverage. Final owned model processes absent; stopped training remains authoritative.

Fresh native Windows preservation observation (no native inference):
`D:\PushTrackML\runs\mac-local-draft-observation-0001\native-preservation-report.json`,
2026-10-13T19:49:27.425049+00:00: original Native GGUF,139protected artifacts and
prepared v2 assets unchanged, remaining native workers0, no training restart.
Mac evidence/source snapshots are archived separately there; no prior run overwritten.

## Use this verified local setup

Subsequent user-approved local CLI installation is recorded in
[0025](0025-local-cli-installation.md); `pushtrack` now resolves to that exact
verified binary. The command below remains the project-build form used at this
proof stage (installation had not yet occurred):

```bash
./target/release/pushtrack --watch \
  --ai-model "$HOME/.cache/pushtrack-dev-evidence/model-store-0002/real-tui-acquisition-0001/cache/pushtrack/models/qwen35-4b-q4km-v2/Qwen3.5-4B-Q4_K_M.gguf" \
  --ai-server "$HOME/.cache/pushtrack/runtimes/llama-b11429-macos-arm64-0001/llama-b11429/llama-server" \
  --ai-python /opt/homebrew/bin/python3.12
```

Alternatively normal `a` downloads into the default model cache, with explicit
confirmation. These verification assets are not silently moved or persisted as
saved settings. Stage intended changes yourself and select the repository before
`m`; review every draft. No automatic commit/push, clipboard or editor action.
Linux actual-model deployment and broader semantic/performance validation remain
unverified; only this specified Mac flow is established. Application changes remain
uncommitted/unpushed; no user CLI installation was changed by this validation.
