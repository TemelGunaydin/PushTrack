# 0033 — Remaining job budget and modal foreground focus

Date: 2026-10-14. User-approved narrow patch, mocked tests, fake-transport PTY and
backed-up offline CLI replacement; **no real inference or private-diff retry**.
The user also requested a dimmed dashboard behind the draft modal and shorter
foreground explanations, based on their supplied screenshot.

## Diagnosis and timeout change

The prior error, `Local draft generation failed: Local draft error: timed out`,
followed explicit approval of a larger context. The independent120s HTTP
completion limit was plausible, **not an observed endpoint diagnosis**: the old
error lacked endpoint labels and completed-job temporary logs were unavailable.
Preparation's60s cap remains another possible cause. No private staged input was
recaptured, tokenized or sent to a model for this patch.

`ml/local_subject.py` now starts a monotonic300s budget at CLI entry, before model
hash verification, and shares it with the owned `LocalCPU` instance. A supplied
deadline can only shorten that fixed budget. Startup keeps its120s upper bound;
complete-source preparation keeps its aggregate60s upper bound, also limited by
remaining job time. Completion's HTTP timeout is **only the remaining job budget**,
not a fresh120s or300s allowance. HTTP responses arriving after the job deadline
are refused, including after decoding. Preparation/readiness also refuse responses
past their stage deadlines. Rust's unchanged300s owned-process timeout and
process-group cancellation remain the hard outer guard; socket timeouts alone
are not a standalone wall-clock watchdog. No retry of completion is introduced.

HTTP timeout messages name an allowlisted endpoint, numerical HTTP budget,
selected context and total job ceiling. Other deadline errors identify startup
or source preparation. They do not print prompts, diffs, paths, URLs, response
bodies or model logs. Response cap, native envelope, all33 reserved source-ID
exclusions, exact source/full-stream roundtrips, marker-free legacy-ID equality,
full-prompt evaluation, EOS/schema/subject gates and owned cleanup are preserved.
The hidden-summary literal-marker refusal is **unchanged**.

## Modal rendering

`src/ui/render.rs` desaturates dashboard cells, removes bold/reverse selection
emphasis and applies DIM before drawing an opaque, cleared draft/model modal.
Foreground cells do not inherit dimming. Monochrome mode uses DIM without RGB
colors; closing restores the normal dashboard. No animation or interaction change.

Draft height falls from16 to14 rows by shortening header/footer copy, keeping the
same body capacity. The repository identity, staged file/byte counts, unstaged/
untracked exclusion, English72-character editing/recheck controls and point-in-time
not-committed status remain. Busy text is `Preparing CPU draft…`; controls appear
once. Capacity still shows exact prompt/output/total/current/required context,
RAM/time and unverified speed/accuracy, no omission, explicit Enter approval and
Esc refusal. Inputs beyond the maximum context do not offer Enter approval.

## Verification and preserved evidence

Private local evidence: `~/.cache/pushtrack-dev-evidence/bounded-timeout-fix-0001/`.
Baseline connector/tests, render and PTY harness were retained before editing.
Two red Python regressions reproduced the independent120s limit and unlabeled
HTTP error; a red render regression reproduced the missing dimmed backdrop.
These intentional failures are retained, not reported as passed runs.

Final proof:

- **41 Python tests**, only synthetic data and mocked time/HTTP/processes. Completion
  receives270s after30s spent, or50s after250s spent; a150s mocked completion can
  finish within the former budget without any actual waiting/inference. Exhausted
  and late budgets are refused. Startup120/preparation60, wrapped/connect/read
  timeout labels, privacy-safe errors and cleanup are covered.
- **62 Rust tests**, `cargo fmt --all --check`, strict all-target Clippy,
  offline/locked release build and whitespace checks passed.
- Render checks cover color/monochrome, all six draft phases,140×36/80×24/60×18,
  a model modal, undimmed foreground and exact dashboard restoration on close.
- Full **release and installed-binary PTY** passed with fake Python/curl/SSH
  transports only. It covers actual muted background ANSI rendering, staged-only
  editing/recheck/stale refusal, explicit context confirmation/cancel, endpoint/
  budget timeout display after expansion, no automatic retry/Git writes, owned
  descendant cleanup, fake download progress/retained partials and terminal restoration.
  The unchanged disk reserve was available; no resource-limited PTY section was skipped.
- Frozen constants and top-level source/output/capacity functions match the saved
  baseline. All Rust/Cargo/catalogue/installer inputs except the intended
  `src/ui/render.rs` match baseline; candidate copies and executed PTY exports retained.

No real model/runtime invocation, large native allocation, asset download, source upload,
Git index/HEAD write, real generation retry, research/data/label/training change or
semantic promotion was performed. Long-context success, quality, RAM and latency
remain **unverified**; the remaining budget can still expire.

## Installation and rollback

The existing installer was run once with:

```sh
PREFIX="$HOME/.local" CARGO_NET_OFFLINE=true CARGO_NET_RETRY=0 ./scripts/install.sh
```

Current CLI/Cargo metadata/private config were backed up before replacement.
Version remains `pushtrack 0.1.0`. Installed bytes equal the tested release;
installed help/version, complete fake-transport PTY and an isolated extracted-
connector literal-input smoke reaching the deliberately absent-model guard passed.

| Identity | SHA-256 |
| --- | --- |
| Previous installed CLI, retained | `a738acac516f41dd15d724adb8f592713d0a431a37526c6afa9feebf8f5db122` |
| New installed/tested release CLI | `9f7d65a3845a4ee26b9282d15120aac606561be5b0ce88e74cb0fb0dfb070de4` |
| New source/embedded connector | `ddaf5dab743fa6ff8e2740f0d12efeb49db9e2806a6dc0e45ad18b55de3c0c99` |

Post-install verification at2026-10-14T12:49:14.330231Z matched config, index/HEAD,
full pinned model hash, runtime files/links, previous CLI and rollback backups.
The user's existing dashboardPID53268 was alive and untouched; no model worker
was observed. The running old process must be quit and restarted normally to use
this replacement. No automatic restart or generation is scheduled.

After quitting PushTrack normally, executable-only rollback:

```sh
cp "$HOME/.cache/pushtrack-dev-evidence/bounded-timeout-fix-0001/pushtrack-before-update" \
   "$HOME/.local/bin/pushtrack"
```

Cargo metadata and private configuration backups are separate; do not blindly
replace newer user configuration. Application/source changes remain uncommitted;
no automatic staging, commit or push.
