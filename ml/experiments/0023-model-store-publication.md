# 0023 — Published small-part model and actual TUI acquisition

## Outcome

Subsequent separately approved Mac runtime/inference validation is recorded in
[0024](0024-mac-native-drafts.md). The acquisition-only boundaries below describe
this historical publication task; no inference was performed during that task.

The user explicitly approved a new <=512MiB packaging/upload attempt after the
v1 deadline/HTTP408 failures. **v2 is published and the TUI downloader enabled**:
https://github.com/TemelGunaydin/PushTrack/releases/tag/model-qwen35-4b-q4km-v2

An asset-only, non-latest **prerelease**, against existing application commit
52247056e753a2e1e6deb11f6212b6deaa0d2fd4. No application code commit/push or branch
update accompanied publication. The old v1 six-asset draft, files and failure
records are preserved. Work remained inline; no delegation, model switching,
training restart, optimizer updates, runtime installation or inference occurred.

## Identity, packaging and publication

Model remains the byte-identical third-party Unsloth Qwen3.5-4B Q4_K_M:
2740937888bytes, SHA-256
00fe7986ff5f6b463e62455821146049db6f9313603938a70800d1fb69ef11a4.
Base/quantization revisions, Apache-2.0 terms, source licenses and limited
experimental quality policy are unchanged. No research-trained CodeT5 model,
datasets, repository diffs, annotations or credentials were published.

Six **raw byte pieces**, not separately loadable GGUF shards: five536870912-byte
pieces and one56583328-byte piece. Concatenate in part01..part06 order, verify
full size/hash before loading. Upstream license/model cards retained; NOTICE
updated only for the new byte-piece instructions. Full piece/notice hashes are
pinned in `assets/models/qwen35-4b-q4km-v2.json`. Manifest SHA-256:
6b71a74a5936aaf83699d065c98eae5ca58b501b85f9b748d6e1df7c64adb3df.

Native Windows preparation:
`D:\PushTrackML\runs\model-release-preparation-0002\report.json`, passed at
2026-10-13T18:33:20.825612+00:00. Source/concatenation matched; **139protected
artifacts unchanged** (the previous132 plus seven preserved v1 package files).
Output: `D:\PushTrackML\releases\qwen35-draft-v2\`.
Mac staging: `~/.cache/pushtrack-release-staging/qwen35-draft-v2/`; independent
byte-integrity checks only, no semantic model evaluation/inference.

A foreground owned controller uploaded files **sequentially**, one bounded `gh`
invocation per asset, no clobber or retries. All11 commands passed: six pieces,
four notices/cards and manifest. Every remote state was uploaded, size and GitHub
SHA-256 digest matched, and the exact expected asset set was reconciled **before**
publication. v1 remained a draft with the same six assets. Publication followed
only this gate; unauthenticated public HTTPS manifest fetch matched the pinned
manifest hash. No credentials were changed or exposed. No uploader remains active.

## Product integration and verification

`src/assets.rs` now uses the immutable v2 catalogue and `RELEASE_PUBLISHED=true`.
The old v1 catalogue remains evidence, not the active download source. No model
identity, inference prompt/context/output policy or quality gate changed. Existing
flags/local-file selection still work; Python and compatible CPU llama-server
b11429 remain manually supplied. Scans never fetch/hash/load models. Only explicit
confirmation downloads; Esc/exit cancels the owned job and keeps partial bytes.

Passed after integration:

- `cargo fmt --all --check`.
- `cargo test --locked`: **52tests**, six suites, latest3.30s.
- `cargo clippy --all-targets --locked -- -D warnings`.
- `cargo build --release --locked`.
- Existing/updated real PTY acceptance using synthetic repos and fake inference/
  fake download transport; actual file-byte progress0.2%, explicit confirmation,
  partial retention and owned descendant termination tested. The PTY driver's
  failure cleanup now requests graceful SIGTERM before forced exit.
- `git diff --check`.

### Actual public HTTPS download through the Mac TUI

Separate proof uses the **real release binary, real system curl and public assets**,
a private cache and a freshly initialized synthetic repository. No `m` action,
model process or inference. No staged source text sent to any network endpoint.

1. Open `a`, confirm `D/Enter`. For this first cancellation check only, a transparent
   wrapper runs real curl with a2MiB/s limit to make interruption reproducible;
   `.curlrc` remains disabled and production HTTPS/timeout/hash rules unchanged.
2. Esc cancels with **1863680bytes** in part01.partial, lock removed, terminal state
   restored. Prefix SHA-256:
   d0247ec07dd376f829e8276768561291fec019574feebda78b887346a4b7a44f.
3. A new explicit D/Enter request with unmodified system curl resumes. Production
   exactHTTP206 range validation passed; prefix bytes preserved exactly. This is
   a deliberate user cancellation/resume, not a hidden failure/retry loop.
4. All pieces/notices and assembled full model passed independent size/SHA-256
   checks, Ready shown, no partial/lock remained, Git status stayed empty, terminal
   restored. Observed Downloading, Verifying SHA-256 and Assembling GGUF phases.

Resume-to-verified-model wall time **435.90s** is one network/IO/crypto observation,
**not inference latency, a distribution, or model RAM/performance benchmark**.
Proof: `~/.cache/pushtrack-dev-evidence/model-store-0002/real-tui-acquisition-0001/`:
executed helper, proof-report.json, download-progress.txt and ready-screen.txt.
Actual verified model and retained pieces/notices stay in that proof's isolated
`cache/pushtrack/models/qwen35-4b-q4km-v2/`; **not automatically moved into the user's
default cache or used for inference**. Normal TUI downloads use XDG_CACHE_HOME,
else ~/.cache/pushtrack/models/qwen35-4b-q4km-v2. ~5.5GB finished cache/~7.5GB cold
free-space requirement remains intentional and documented.

## Preservation and limits

Fresh native observation:
`D:\PushTrackML\runs\model-store-observation-0002\native-preservation-report.json`,
2026-10-13T19:21:16.971496+00:00: original GGUF unchanged,139protected artifacts
unchanged, all11prepared v2 assets unchanged; zero inference/optimizer updates.
Separate post-helper native process observation: **zero owned Python/server workers**.
Pause evidence and71measured training epochs remain authoritative; no restart.

Mac evidence: `~/.cache/pushtrack-dev-evidence/model-store-0002/` contains one-shot
upload logs/controller, remote reconciliation/publication snapshots, public manifest,
actual acquisition proof and native preservation log. Archive summaries use distinct
filenames; previous [0022](0022-model-store.md) collision/recovery evidence remains
preserved rather than overwritten or rerun.

**Still unverified:** compatible native Mac/Linux runtime setup and full actual-model
`m` generation/edit/stale-check/cancellation/resource flow. Acquisition success does
not establish model semantic accuracy or production promotion. Python/runtime
installation and target inference require the separately scoped user approval;
no runtime assets installed in this task. Current application changes are local,
uncommitted/unpushed; the model release is published independently.
