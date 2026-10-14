# 0026 — Plain watch runtime discovery and Ready selection

2026-10-13. User reported: model acquired with `a`, Enter repeatedly showed
verification/byte progress, then `m` failed to locate llama-server. Work inline,
no delegation or training restart, no new runtime/model download or system PATH
change. Existing app/source changes and user's open dashboard were preserved.

## Causes established before fixes

- Config resolution checked explicit `--ai-server`, then PATH only. The verified
  Mac ARM64 b11429 server existed in its private supported cache but not PATH.
  Running plain `pushtrack --watch` therefore failed despite successful prior
  manual-path proof. Existing runtime `--version` confirmed clean d81235049.
- Model dialog Ready phase still used the general Enter branch: `SelectModel`.
  That reread/checksummed the existing2.74GB model. The user's byte counter was
  local SHA-256 verification, **not a network download**. A new regression test
  failed before the patch: SelectModel instead of expected CloseModels.

## Narrow changes

- `src/assets.rs`: share existing XDG/HOME cache-root resolution and expose only
  the known Mac ARM64 b11429 cache path. No directory creation/network work.
- `src/draft.rs`: explicit server path retains priority, then PATH, then the
  already installed supported cached server. Unsupported platforms/missing cache
  retain explicit setup error. No provider fallback, runtime install or weakened
  clean-version/model-hash/context/input checks.
- `src/ui/models.rs`: Ready Enter closes the selection window; Busy Enter remains
  ignored, confirmation still explicit. Choosing a different row returns Browse.
- `src/ui/render.rs`: Checking local file SHA-256 label and Ready Enter/Esc return
  instructions make local byte progress unambiguous.

Inference still checks full pinned GGUF before each load; completed selection does
not bypass it. No inference prompt/token/output/model changes or Cargo additions.

## Proof and installation

- Red Ready Enter regression retained at
  `~/.cache/pushtrack-dev-evidence/watch-ai-discovery-fix-0001/red-ready-enter.log`.
- **55Rust tests**, six suites,3.22s passed: new Ready Enter regression, explicit/
  PATH priority and cached-runtime/missing-runtime cases, prior52checks preserved.
- fmt, strict Clippy, release build, all existing PTY acceptance passed.
- Installed via existing locked/offline/no-sudo installer after preserving prior
  `~/.local/bin/pushtrack` as `installed-before-fix` and saved settings fingerprint.
  No existing user dashboard was killed; its mapped old executable requires a
  normal quit/restart to use the update. No PATH/config/model moves or code push.

Actual **installed binary**, plain `--watch`, synthetic repository proof:
`plain-watch-proof-0001/proof-report.json`. No ai-model/server/python flags used;
real cached model verification, Ready Enter closed, `m` returned
**Add TIMEOUT constant to constant.py** in17.65s. Runtime discovered from cache,
default existing Python used. Curl was replaced **only in the test environment**
with a fail/record guard: **zero curl calls**, no new downloads. Index/HEAD unchanged,
terminal restored and model server exited. This reuses one simple synthetic edit,
not a new accuracy or broad performance assessment.

Evidence, backup, logs and executed helper retained in
`~/.cache/pushtrack-dev-evidence/watch-ai-discovery-fix-0001/`.
User models/verified runtime/saved-folder configuration remain unchanged; all
previous model/research/development gate/pause evidence is preserved.

## User flow

Quit the old dashboard normally (`q`), then run **`pushtrack --watch`** again.
Model is already cached; **do not redownload it**. If using `a`, Enter checks local
hash once; when Ready, another Enter returns. Select a repo, stage its intended
text changes yourself, then `m` for an editable local draft. No automatic Git writes.
Explicit runtime flags/PATH retain priority; new supported-cache discovery is
only for the already installed pinned native Mac ARM64 runtime.
