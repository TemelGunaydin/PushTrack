# 0027 — Complete-input capacity and explicit larger contexts

2026-10-14. User approved `ekle` after reporting the generic Git output bound
following `git add .`. Inline work, no delegation, automatic Git writes, downloads,
source uploads, training/research data processing or installed CLI replacement.

## Acceptance and constraints

- Keep the entire selected staged snapshot, file accounting and UTF-8 checks;
  never omit/truncate files, hunks, audit roles or model tokens.
- Show files/bytes and, when supported, exact **whole-policy-prompt** token needs.
- Keep4096default/192output/2CPUthreads and unchanged SYSTEM/schema/literal audit.
- Do not automatically allocate a bigger context or complete oversized input;
  require a separate explicit Enter approval after the measured capacity screen.
- Preserve control/binary/symlink/gitlink/conflict/version/hash/EOS/truncation gates
  and stale snapshot checks. Historical quality judgments remain4096-only.

## Diagnosed input

At inspection:88stagedfiles; complete patch844639bytes, SHA-256
15bd24d9a1a676134212b1f924a384f7848c59ccce885e2ceeff71f8e8c5feba.
Raw metadata11214bytes and numstat2997bytes fit; patch exceeded the old262144bound.
Read-only local counters revealed reserved markers inside source/security tests:
2 im_start,3 im_end,2 endoftext occurrences. These are **still explicitly refused**.
No valid whole-policy prompt exists for this scope under the current control gate;
no exact token count/completion is claimed or synthesized by sanitizing it.

After change the exact same844639byte input fits4MiB but fails unchanged control
validation before weights load. `current-index-preflight.json` retains byte/hash,
policy error and token_count:null. Source code in the index was not rewritten;
index fingerprint remained451f6e0dd4ba376a1684b044fcfb4d910af6d1dc04de1f15e18612ed86a81ce8.

## Implementation

- `src/draft.rs`: complete capture cap4MiB; descriptive oversized-input error.
  Collected snapshot update exposes files/bytes even on later policy refusal.
  Capacity JSON is validated against exact byte size,192reservedoutput,
  requested context and minimum supported recommendation. Unknown/malformed
  metadata cannot launch a job. Staged/HEAD/branch rechecked before confirmation
  generation, after generation and when reviewing the edited subject.
- `ml/local_subject.py`: max4MiB; `prepare` applies unchanged native template,
  ensures complete diff appears once, lossless raw tokenizer roundtrip and counts
  every rendered prompt token. `--capacity-report` returns JSON/exit2 without
  `/completion` if the requested context cannot fit. `--check` measures only at
 4096. Normal small-input stdout remains one subject; EOS/full evaluation checks
  unchanged. Local response bound32MiB accommodates larger complete templates/
  token IDs and remains capped; endpoint/proxy/device restrictions unchanged.
- `src/ui/draft.rs`, `mod.rs`, `terminal.rs`, `render.rs`: capacity phase shows
  exact prompt +192reservation/current/recommended context. Enter confirms only
  a fitting larger context; Esc declines; impossible fit cannot start. No inference
  upon scan/refresh, no persisted settings or automatic context fallback.

Choices:4096,8192,16384,32768,65536,131072,262144. Recommendation is smallest
choice fitting the full prompt + output reserve, not arbitrary default expansion.
Pinned model native context ceiling bounds choices; no RoPE/model/provider changes.
Larger generation remains experimental, potentially high RAM/time; existing
300s owned-job deadline and cancellation remain. **No long-context accuracy,
completion performance or peak RAM is established**, even when token counts fit.
Historical32case/18usable development gate is not extended to these large inputs.

## Tests and failures retained

**60Rust tests**,23standard-library Python connector tests, strict Clippy,
release build, fmt and PTY tests passed. New proofs cover:

- >256KiB capture retains every byte, index unchanged; >4MiB/invalidUTF8 refused.
- Complete-prompt counts/recommendation, max-context refusal, malformed capacity
  JSON, default4096 and explicit8192forwarding without GPU/offload.
- No `/completion` from measurement/oversized default; no expansion before Enter;
  Esc declines; confirmed job uses8192; stale index refuses before backend start.
- Capacity rendering at140x36/80x24/60x18 and existing edit/cleanup/signal flows.

First Rust run used the old receive-once fixtures; Collected progress is now an
intermediate update, so fixtures drain it before asserting a terminal result.
Old270KB oversize case moved to4MiB+1; >256KB preservation added explicitly.
PTY failure1 matched old generation text across a new line wrap; changed test to
actual measurement label. Failure2 observed a partial differential screen while
scheduling confirmation; test now waits for complete capacity title/count/footer
and fully cleared old frame. No production cancellation or confirmation rule
was weakened. Failed label log, confirmation diagnostic note and corrected third
PTY log are retained separately; no proof directory reused/overwritten.

## Actual native check, without costly generation

`~/.cache/pushtrack-dev-evidence/draft-capacity-0001/actual-tokenization-0001/`:
private synthetic unborn-HEAD repo with300000'x'bytes plus newline staged as
large.txt. Worktree release binary ran plain `--watch`, real pinned cached GGUF
and native Mac ARM64 CPU runtime. **Only baseline4096 allocated**; retained live
argv confirms2threads/noGPU/nooffload/no context shift and unchanged CPU flags.

TUI displayed1file,293.2/4096KiB; exact prompt75520+192=75712tokens and recommended
131072context in6.114s to observed capacity. Only tokenization/template/roundtrip:
**no diff completion, no larger context approval/allocation**. Driver chose Esc,
then q; index/HEAD unchanged, terminal restored and owned model process gone.
Curl fail/record guard was used only in test environment; zero calls/no downloads.
This one highly repetitive synthetic input is not a representative resource or
semantic benchmark. It proves real capacity plumbing, not131072generation.

Evidence/helpers/logs remain outside Git at
`~/.cache/pushtrack-dev-evidence/draft-capacity-0001/`. Source binary differs from
installed CLI, which was intentionally not replaced without follow-up approval.
Model/runtime/config/index/training remain unchanged; no code commit/push.

## Handoff

Subsequent separately approved CLI installation is recorded in
[0028](0028-capacity-cli-installation.md). The paragraph below records this
feature proof's pre-install handoff state:

User must approve installed CLI update separately. Once installed: `m` shows
files/bytes; a valid oversized-context prompt offers an explicit Enter approval.
For the current staged scope, a separate reserved-marker policy question remains:
input is not silently sanitized or made safe by increasing context. Handling
literal reserved markers as source data would require a separately approved,
lossless framing/token-boundary safety design and fresh regression/semantic proof;
this task does **not** bypass the existing refusal or promise this diff a subject.
