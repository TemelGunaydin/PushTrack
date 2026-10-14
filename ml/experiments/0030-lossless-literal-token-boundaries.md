# 0030 — Lossless literal token boundaries: synthetic token-only proof

2026-10-14. User approved the alternate interior-boundary candidate (`EVET`)
after [0029's native USER_DEFINED blocker](0029-literal-marker-contract-blocker.md).
Inline only. This proves token handling, **not semantic generation, deployment,
large-context allocation or private staged-scope capacity**. Installed CLI remains
unchanged; no source upload/download or research/training work was performed.

## Exact mechanism and fail-closed contract

`ml/local_subject.py` freezes all33CONTROL/USER_DEFINED spellings and IDs
248044..248076 from the exact hash-pinned Qwen3.5 GGUF. Raw diff and entire user
message (including the unchanged literal line-role audit) are sliced **after the
opening `<` inside registered spellings**. Only tokenization boundaries change:
no escaping, inserted delimiters, character replacement, normalization, omission
or altered audit roles. Every resulting source chunk is ordinary-tokenized with
`add_special=false,parse_special=false`; all33IDs are excluded independently from
every chunk, hence also from their concatenated source IDs. The six problematic
USER_DEFINED tags are never merely allowed as source tokens.

Each chunk and the combined raw-diff/full-user streams must detokenize exactly.
Native rendering must byte-equal frozen trusted prefix + full user + suffix and
contain the raw complete diff exactly once. Prefix/suffix alone are special-aware;
expected structural ID sequences are checked. Combined prompt IDs must detokenize
with `special:true` to the full native rendering. Marker-free prompts additionally
must **match the legacy whole-rendering token IDs exactly**, otherwise fail for
compatibility review. No unsafe fallback. Final concatenated IDs drive capacity
and completion input; default4096/output192, 4MiB capture, fixed larger-context
confirmation and existing300s owned-job deadline are unchanged.

Combined raw-diff/full-user chunk count is capped at128, with explicit refusal
before weights/HTTP for excess; never omit excess data. Preparation has a60s
aggregate deadline (per-request timeout uses remaining time), within the existing
owned-job bound. Per prepare at most263 measured API calls: at most256 chunk
calls, two combined-source detokenizations, template, two trusted tokenizations,
full-stream detokenization, and optional legacy comparison; startup readiness is
separately bounded as before. Existing32MiB response cap remains. Python input
checks now also mirror existing Rust DEL/C1/bidi/invisible-control refusal;
permitting registered literal text does not weaken encoding/control gates.
SYSTEM/schema, audit semantics, Git accounting/stale checks, CPU flags, process
ownership and output/EOS/full-evaluation/subject gates remain unchanged.

## Fresh evidence and observed results

Private evidence: `~/.cache/pushtrack-dev-evidence/literal-marker-boundaries-0001/`.
Original connector/tests and installedCLI/index/HEAD-reference/config fingerprints
were saved before edits. Earlier blocker evidence and failed contract remain intact.
Candidate connector SHA256:
`b0755369dcb50e8ffa587ff46b26dbebd5c325e0098269eedce1a536673a4779`.

- **33 Python tests passed**: all33literal preservation, additions/removals/context/
  filenames/hostile role tags, source-ID leaks, mutated template/chunk/user/full
  roundtrips, bad token types, trusted control sequences, legacy mismatch,
  amplification cap before runtime and preparation deadline, plus existing gates.
- **60 Rust tests**, fmt, strict Clippy and release build passed.
- Initial Rust run hit the unchanged asset disk-reserve gate; all five failures
  and logs were retained. Later available-space observations differed; focused
  existing asset proof passed, then a fresh full60-test run passed. No production
  reserve change, deletion or model-download retry. The exact earlier free-space
  value was not sampled, so no precise reclaim mechanism is asserted.
- Relevant **task-only PTY prefix passed**: dashboard/resize/monochrome, terminal
  restoration/signals/fetch cancellation, staged-only draft/edit/stale checks,
  explicit capacity confirmation/decline and owned model-descendant cleanup.
  The unchanged script's final managed-download section was not executed: observed
  available4,983,730,176bytes was below its7,481,875,776-byte reserve. Executed
  prefix is retained; this is **not a full PTY suite pass**. No guard was weakened.
- **44 synthetic native cases passed** at4096 only, pinned GGUF hash and clean
  Mac ARM64 b11429/d81235049, same CPU2/no-offload flags. Cases include each of
  all33registered literals, all33together, removed/context/filename/hostile roles,
  CRLF/unicode and four marker-free legacy cases. Source IDs excluded all33;
  chunk/user/fullstream roundtrips and trusted native envelope equality passed.
  All four marker-free cases had exact native legacy ID identity. Per-input
  runtime compatibility gate remains mandatory, not a universal population claim.
- Recorded native measured endpoints:44 `/apply-template`,421 `/tokenize`,461
  `/detokenize`, **zero `/completion`**; normal startup readiness not included in
  those counts. Chunk-budget refusal issued no endpoint call. Server exited.
  Observed proof-body wall time3.115561s is token mechanics on small synthetic
  inputs, not completion latency, cold-cache performance or a resource guarantee.
  An external120s owned-group controller bounded the probe; no larger context.

Evidence contains `native-proof-0001/report.json`, executed helper, actual argv,
server logs, source/test backups, failed and corrected gate logs, task-only PTY
prefix, final preservation report and candidate snapshots. No normal source/index
writes beyond the approved worktree implementation/docs; synthetic test repositories
are separate from the user's repository.

## Deliberately not established

No subject was generated with this alternate literal-token path. No current88file/
844KB private staged diff was tokenized through the model; exact capacity still
unknown. No larger-context allocation, quality/RAM/latency promotion, CLI replacement,
Git stage/commit/push, source upload/download, dataset/label update or training
restart. Historical18/2/0 development judgments do not become literal-input or
long-context semantic evidence. Installed e7ba1bcd99aabecfa74fc25bab1696861a3ca7843c56e6db2088fea23bcb2e72
still has its original literal-marker refusal. Subsequent small synthetic semantic
generation, private-input measurement or deployment each needs separate approval.

Subsequent small synthetic generation was separately approved and observed in
[0031](0031-literal-input-generation-probe.md): two accepted drafts and one unchanged
internal-summary output-gate refusal. This does not alter the token-only scope or
results of0030, and no CLI deployment followed.
