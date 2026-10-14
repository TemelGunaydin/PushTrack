# 0029 — Literal-marker token contract: blocked before implementation

2026-10-14. User approved `tamam` for a lossless source-token candidate and bounded
native4096tokenization-only proof, with an explicit stop if `parse_special=false`
still emits USER_DEFINED/control IDs. Inline only; no new source-token policy,
CLI replacement, completion, larger context, download, source upload, Git/index
writes, dataset processing, training restart or automatic workaround.

## Proposed invariant and minimum probe

Pinned Qwen3.5 GGUF vocabulary metadata identifies33CONTROL/USER_DEFINED IDs
248044..248076. Source data (raw diff plus unchanged literal audit) must produce
**none of these IDs**. Trusted native template prefix/suffix alone may contain
structural control tokens; raw source must remain byte-identical. Model/string
escaping, omission, silent source modification or merely dropping the old blacklist
is not a safe implementation.

Before editing `ml/local_subject.py`, saved unchanged connector/tests and
connector/installedCLI/index/HEAD/config fingerprints in fresh private evidence:
`~/.cache/pushtrack-dev-evidence/literal-marker-tokens-0001/`.

`executed-contract-probe-0001.py` used only a synthetic complete unified diff with
all33spellings as source literals. Full pinned GGUF hash and clean native b11429/
d81235049 runtime verified. One owned native Mac ARM64 server at4096context,
CPU2threads/GPUoff, same existing runtime flags and proxy-disabled loopback.
External controller bound65seconds with owned process-group termination on timeout.
Measured calls: /tokenize,/detokenize,/apply-template,/tokenize,/tokenize,/detokenize;
normal startup also observes /health. **Zero /completion, zero larger-context
allocation.** Server exited normally.

## Actual observations

- Entire user text `parse_special=false,add_special=false` tokenization:
  **six USER_DEFINED IDs still present**, repeated for original source and audit.
- These IDs/spellings:
  -248058 `<tool_call>`;248059 `</tool_call>`
  -248066 `<tool_response>`;248067 `</tool_response>`
  -248068 `<think>`;248069 `</think>`
- User text roundtrip **true**.
- Native rendered template byte-equals trusted prefix + full user + suffix: **true**.
- Full segmented token stream detokenized with `special:true` byte-equals native
  rendering: **true**.
- Reserved im_start/im_end/endoftext literals did not appear as their control IDs
  in this ordinary user token stream. This does **not** prove all33safe: the six
  USER_DEFINED exceptions fail the selected source-ID exclusion invariant.

Evidence: `contract-probe-report.json`, `probe-argv.txt`, `probe-server-logs/`,
original source/test snapshots, prechange state and executed helper. This is a
successful observation of a **failed safety contract**, not generation or an
exploit demonstration. Tools/agents remained disabled; no claim that each six
USER_DEFINED token causes a role escape or an executed tool call is made.

## Stop and next decision

Approved plan says to stop on this exact result. **No product code/test change**
or model-control blacklist removal was made. No new unit/Rust/PTY suite claim:
existing60Rust/23Python evidence is historical/current-unchanged only. Installed
CLI remains e7ba1bcd99aabecfa74fc25bab1696861a3ca7843c56e6db2088fea23bcb2e72;
connector remains82270aa5e22babe84fb2201dd8519f74801290dfbc3e058918ba0f26dc89f762.

Possible follow-up requires separate approval: an explicit **interior token
boundary split** within the six registered literal spellings, preserving source
characters/order and detokenized bytes, not escaping/replacing them. Every
resulting source chunk must exclude all33special IDs; concatenated whole-user and
full-stream roundtrips/template equality remain required. Token counts must use
the final concatenated IDs, which may increase; marker-free baseline token-ID
compatibility needs a fresh check. Runtime call/chunk amplification must be bounded
and excess refused without omitted data. This is a design proposal, **not an
implemented/tested workaround**, and remains subject to native synthetic proof.

Do not invoke actual completion or deploy without subsequent approval. Current
88file scope may still exceed262144context even if source markers become supported;
no private-scope token count or future successful subject is promised.

Subsequent `EVET` approved only the interior-boundary candidate and synthetic
mechanics proof. [0030](0030-lossless-literal-token-boundaries.md) records that
follow-up; it does not change or erase this original failed contract.
