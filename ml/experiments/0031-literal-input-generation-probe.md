# 0031 — Literal-input generation: two accepted drafts, one output-gate refusal

2026-10-14. User approved a few small synthetic semantic-generation checks after
[0030's token-only proof](0030-lossless-literal-token-boundaries.md). Inline,
unchanged candidate/policy/guards, pinned existing GGUF/b11429 CPU runtime,
4096context/192output only. **No installation or production promotion.**

## Predeclared fixtures and owned execution

Fresh private evidence:
`~/.cache/pushtrack-dev-evidence/literal-marker-generation-0001/`.
Before inference saved connector/tests and installedCLI/index/HEAD/config identities,
all runtime regular-file hashes/relative links, and prior gate-report identity.
Candidate remains
`b0755369dcb50e8ffa587ff46b26dbebd5c325e0098269eedce1a536673a4779`.

`predeclared-cases.json` froze exactly three edits, expected subject scope and
unsupported claims. Separate synthetic Git repositories produced complete patches;
Git dry-run cached application (reverse for the newly added file) passed. Fixture
Git writes are isolated, never the user's repository. Source snapshots/diff hashes
are retained. No research datasets were used.

1. **349bytes:** TIMEOUT10→20; one unchanged comment contains the three reserved
   control spellings and all six problematic USER_DEFINED tags. Expected the
   constant change, not new marker/parser/tool functionality or invented units.
2. **325bytes:** new `user_markers.py` defining USER_DEFINED_MARKERS as six strings
   (`tool_call`, `tool_response`, `think` opening/closing tags). Expected a new
   literal constant, not implemented tool/thinking/parsing/security behavior.
3. **300bytes:** existing empty CONTROL_MARKERS tuple populated with the three
   literal strings `im_start`, `im_end`, `endoftext`. Expected a tuple-value edit;
   explicitly anticipated that unchanged output validation might refuse literal
   echo. No refusal may be laundered into an accepted subject.

Existing GGUF full SHA256 and clean b11429/d81235049 runtime verified. One owned
loopback server, same CPU2/no-GPU/no-offload/no-tools/no-context-shift flags. Exactly
**one completion per fixture, three total**, temperature0/seed42/cache_promptfalse;
no retries, target-aware selection, policy changes or fallback. Exact prepared
integer prompt IDs forwarded unchanged. External owned-group controller bound240s,
within the application300s job bound. Server/group exited after the run.

## Observed mechanics and outcomes

| Case | Prompt tokens | Generated tokens incl. EOS | Product outcome |
|---|---:|---:|---|
| TIMEOUT with literal context |579|41|Accepted: `Increase TIMEOUT constant to 20`|
| New USER_DEFINED tuple |593|56|Accepted: `Add user_markers.py with tool and thinking marker constants`|
| Populate CONTROL_MARKERS |567|58|Refused: `Invalid internal edit summary controls`|

All three native preparations excluded all33reserved IDs from source chunks and
combined source data, preserved exact chunk/raw/user/fullstream bytes and matched
the trusted native envelope. Complete prompts evaluated (579/593/567),
`truncated:false`, `stop_type:eos`, final token248046. Default4096 fitted each
complete prompt plus192; no context increase or omission. Measured endpoints:
3 `/apply-template`,57 `/tokenize`,60 `/detokenize`,3 `/completion`; normal startup
readiness is outside those counts.

Unblinded assistant review against predeclared edits: first accepted subject is
usable and precise. Second is usable but interpretation-sensitive: tool/thinking
terminology derives from tag names; internal summary's “thinking processes” is
not evidence of implemented behavior. Manual editing/review remains required.
These are not independent human gold or population-accuracy estimates.

Per-case observed wall times13.674/14.774/14.407s include preparation+completion
inside an already started server. Run body45.737s included startup/cleanup, not
full TUI/model-hash startup or a cold-disk/peak-RAM benchmark. No distribution or
performance guarantee is established.

## Concrete remaining blocker: output role, not input losslessness

Third raw JSON accurately describes replacement of an empty tuple and reproduces
its three added literal strings in the **non-displayed `edit_summary`**. Existing
`draft()` rejects any of those character spellings in that field, even inside
valid JSON text. Full-prompt/source checks and EOS had already passed.

A no-model/no-retry replay of that saved response reproduced the exact refusal.
Internal summary contains no C0 characters; returned output token IDs contain no
reserved ID except terminal EOS248046. Its raw proposed subject passes the
subject-only guard, but **the complete draft remains rejected** and was not
accepted/delivered. Saved proposed text is diagnostic evidence, not a successful
product output. No marker escaping, subject extraction bypass, rewritten response,
gate removal or second completion was used.

Evidence: per-case `prepared.json`, exact `completion-request.json`, actual
`completion-response.json`, `observation.json`; `native-run-0001/report.json`,
executed helper/connector, actual argv/server logs, `semantic-review.json`,
`output-gate-diagnosis.json`, and final preservation report. Prior33Python/60Rust
and task-onlyPTY results are reused by unchanged connector/test identities, not
represented as a new full test run. Full managed-downloadPTY remains separately
unrun due disk reserve.

## Stop and separate next decision

This is **two accepted development drafts plus one unchanged output-gate refusal**,
not all-cases semantic success, broad marker support or deployment clearance.
No product code/test change, current private staged-scope measurement/generation,
larger context, CLI replacement, source upload/download, user-project Git/index
writes, dataset/target/approval-flag update or training restart. Installed CLI still
retains its original input-marker refusal.

Possible follow-up requires separate approval: read-only role-specific output
contract design for literal strings inside the non-displayed validated JSON
summary, while preserving source-ID exclusion, encoding/C0/bidi, schema, full
prompt/EOS and subject/terminal safeguards. No output policy change or further
completion is authorized by this probe. Historical quality judgments are unchanged.

Subsequent user `uygula` separately approved installing the already-tested input
candidate: [0032](0032-literal-token-cli-installation.md). That installation retains
this output refusal and does not change the scope or results of0031.
