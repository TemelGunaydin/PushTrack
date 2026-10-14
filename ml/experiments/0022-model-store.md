# 0022 — Explicit TUI model acquisition and GitHub release preparation

## Historical status (2026-10-13, before v2 publication)

**Superseded publication status:** the user approved smaller pieces and v2 is now
published; actual TUI acquisition passed. See [0023](0023-model-store-publication.md).
The failures/proof below remain historical evidence, not current availability.

**Implementation verified; public model hosting blocked.** The dashboard has
`a` model/source selection, explicit download confirmation, byte-based progress,
SHA-256 verification, assembly, cancellation and safe existing-file selection.
The model release is still a **draft with6/7assets**; part01 did not upload.
`src/assets.rs::RELEASE_PUBLISHED=false` intentionally prevents public acquisition
until a complete release is verified and published. No background retry is scheduled.

The user requested GitHub model storage and TUI selection/loading progress, then
stopped/resumed work. Work stayed inline; no delegation or model switching.
The stopped hundred-epoch CodeT5 run was **not restarted**. No inference/training,
Git staging, code commit/push, branch update, or runtime/Python package installation was
performed for this task. A GitHub **asset-only draft release** was created against
existing commit52247056e753a2e1e6deb11f6212b6deaa0d2fd4; it is not an app release.

## Unchanged model identity and terms

- Model: Qwen3.5-4B Q4_K_M, third-party **Unsloth**, not official Qwen GGUF.
- Base revision:851bf6e806efd8d0a36b00ddf55e13ccb7b8cd0a.
- Quantization revision:e87f176479d0855a907a41277aca2f8ee7a09523.
- Bytes:2740937888.
- SHA-256:00fe7986ff5f6b463e62455821146049db6f9313603938a70800d1fb69ef11a4.
- Apache-2.0. Full upstream license/model cards and a redistribution notice accompany
  acquisition. Runtime remains separately trusted llama.cpp b11429, MIT.
- No research datasets, CodeT5 checkpoints, source diffs, annotations or credentials
  are redistributed. Dataset CC BY-NC restrictions/uncleared research-trained weight
  distribution are not claimed resolved by these pretrained-model terms.

No optimizer updates were applied to this model. Prior limited/unblinded development
quality evidence and all original labels/approval flags remain unchanged. This does
not establish population accuracy, production promotion or Mac/Linux performance.

## Packaging and publication evidence

GitHub requires every release asset to be <2GiB. The unchanged GGUF was split into
byte-concatenable pieces **natively on Windows**, not re-quantized:

| Asset | Bytes | SHA-256 |
|---|---:|---|
|Qwen3.5-4B-Q4_K_M.gguf.part01|1500000000|416e11f3cf0391279546e73fd7a3658c368ae4328f0a94d34b6d7d6d0394964f|
|Qwen3.5-4B-Q4_K_M.gguf.part02|1240937888|d4761367a069f853868471b7c11cd9a65c6112e5d9476b9c3ac2bd32bcebacfb|

Concatenation reproduced the full pinned hash. Original model and132protected
artifacts were unchanged. Preparation evidence:
`D:\PushTrackML\runs\model-release-preparation-0001\report.json`.
Windows prepared files:
`D:\PushTrackML\releases\qwen35-draft-v1\`.
Mac staging copy (integrity checked; **no inference**):
`~/.cache/pushtrack-release-staging/qwen35-draft-v1/`.

Release tag:model-qwen35-4b-q4km-v1, repository:TemelGunaydin/PushTrack.
An initial seven-file upload command hit its1800-second controller deadline.
Reconciliation confirmed6uploaded assets: part02, LICENSE.txt, NOTICE.md, both
upstream model cards, model-manifest.json. Their GitHub size/digest matches the
pinned manifest; the manifest SHA-256 is
0c5a5bd898cb1a281414f3a4f679a15236b2ec51b4a350993722d14a7ba17a76.
No uploader remained active. Publication was withheld rather than presenting a
partial release as ready.

After explicit user resume, a single missing-part upload was allowed a3600-second
limit, with no clobber/overwrite. It failed with:
`HTTP408: Upload body timed out due to inactivity`.
A separate read-only reconciliation again found6assets, a draft release, no
part01, and no active owned uploader. **The inactivity failure does not prove file
size alone caused it**; smaller pieces are only a proposed mitigation requiring
new user approval, not an executed fix or guaranteed solution. No automatic retry,
authentication workaround, metadata sweep or incomplete publication followed.

## Implementation and ownership

- `assets/models/qwen35-4b-q4km-v1.json`: built-in pinned public manifest. No remote
  mutable catalogue, provider credentials or unreviewed model alternatives.
- `src/assets.rs`: owned worker and model-cache installer. Existing system `curl`
  handles public HTTPS transport; `.curlrc` ignored, retry0, connection/idle/total
  deadlines, response/file bounds, exact206 resume ranges. All parts/notices/full
  model verified with SHA-256. Wrong files fail without replacing them.
- `src/process.rs`: existing bounded owned-process runner gains an observation
  callback; cancellation/timeout/output caps/group-descendant cleanup retained.
- `src/ui/models.rs`, `render.rs`, `terminal.rs`: selection/confirmation/busy/ready/
  error phases. Gauge uses actual file bytes, then hash/assembly progress; speed
  and approximate ETA are measured, not a synthetic loading timer. Single modal
  job, Esc cancellation, Ctrl+C/q exit, worker-disconnection error handling.
- `src/draft.rs`: manual flags still supported; managed model path and a trusted
  `llama-server` on PATH can be used without paired flags. Python/runtime remain
  manually supplied. Loading still checks the exact GGUF and pinned runtime;
  all staged-input, token/context, review and stale-snapshot invariants remain.
- `.gitignore`: GGUF/partial weights protected from accidental ordinary Git commits.
- Cargo adds `sha2` and the existing nix `fs` feature for actual integrity/disk checks;
  no HTTP provider, inference runtime dependency or package installer is added.

Cache:$XDG_CACHE_HOME/pushtrack/models/qwen35-4b-q4km-v1, otherwise ~/.cache/... .
Cold acquisition requires ~7.5GB free including reserve, retains verified byte
parts/notices (~5.5GB finished cache), and publishes the full file atomically
without clobbering. Cache locks prevent overlapping installers. Cancellation keeps
partial download bytes and removes only owned temporary assembly/lock state. No
scan/refresh/key navigation starts downloads, hashes weights, or performs inference.
Only a confirmed download can fetch, and only Enter can verify an existing file.

## Verification

Mac synthetic tests; **no new actual-model inference**:

- `cargo fmt --all --check` — passed.
- `cargo test --locked` — **52tests passed**, six suites (latest3.14s).
- `cargo clippy --all-targets --locked -- -D warnings` — passed.
- `cargo build --release --locked` — passed.
- `uv run --no-project --with pyte scripts/test_tui.py target/release/pushtrack` — passed.
- `git diff --check` — passed.

Ten new tests cover catalogue/piece integrity, exact assembly/notices and no
redownload,206 prefix preservation/ignored-range refusal, corrupt-file retention,
symlink/oversize/lock refusal, one-shot transport failure, owned download descendant
cancellation, metadata path/duplicate/account restrictions, scoped confirmation and
progress rendering at140x36/80x24/60x18. Payloads are tiny synthetic fixtures and
transport is fake curl: **not a real GitHub downloader or full target deployment
proof**. PTY checks retain prior scan/draft/cleanup assertions and add model/source
selection, explicit confirmation, safe publication refusal and no download job.

One failed resume fixture used padded `wc` output in a synthetic Content-Range;
normalizing the test fixture fixed it without relaxing the production range gate.
A failed PTY immediate assertion captured a partly painted frame: waiting for all
required labels fixed test synchronization; production layout was not changed.
Earlier failed upload attempts remain represented, not overwritten or called passed.

Fresh native preservation observation:
`D:\PushTrackML\runs\model-store-observation-0001\report.json`,
2026-10-13T18:23:39.306172+00:00: original model unchanged,132protected artifacts
unchanged, zero inference/optimizer updates; separate native process observation
found **zero owned Python/llama-server workers**. Executed helper archived alongside
that report. Stopped training/pause evidence remains authoritative.

**Archive naming collision recorded:** SCP initially reused `report.json` for the
application summary in this newly generated observation directory. The summary
was retained as `application-summary-0001.json`; the preservation observation was
restored from already captured native stdout with its original timestamp/writer
serialization, without rerunning the verifier. `evidence-recovery-0001.json`, the
captured source and executed recovery helper record both payloads/hashes. No model,
checkpoint, earlier evidence or protected artifact was affected. The original
application snapshot is retained; this documentation correction is a separate copy.

## Remaining scope

1. Obtain approval for a revised bounded hosting attempt. Proposed: a **new**
   versioned draft with <=512MiB byte pieces, preserving the existing failed draft,
   original model and evidence. No change to full-model identity/quality policy.
2. Reconcile every asset size/hash, publish only a complete release, update the
   built-in catalogue/publication gate, then exercise real user-triggered download,
   resume/cancellation/integrity and the full TUI with public assets.
3. Compatible target llama-server installation and actual-model Mac/Linux dashboard
   inference remain unverified and outside this completed synthetic proof. No
   runtime transfer/install or target inference has been started.
