# 0028 — Install capacity-aware CLI

2026-10-14. User approved `evet` after [0027](0027-draft-capacity.md) handoff.
Inline installation only: no product/policy changes, downloads, real inference,
large context allocation, dataset processing, training restart, Git/index writes,
sudo, system/security/PATH modifications or model/runtime/cache moves.

## Identity and preserved state

Current `pushtrack` resolved to `~/.local/bin/pushtrack`, old SHA-256:
32d6f4aa1dd872f6103362f233f6fda763783300fc6bab9c1af5ee64e957fe08.
Candidate SHA-256: e7ba1bcd99aabecfa74fc25bab1696861a3ca7843c56e6db2088fea23bcb2e72;
embedded connector82270aa5e22babe84fb2201dd8519f74801290dfbc3e058918ba0f26dc89f762.
Reconciled30real archived source files against0027snapshot before installation;
therefore still-current60Rust/23Python/fmt/Clippy/release/PTY/actual4k tokenizer
checks were reused, not a new long-context semantic or performance promotion.

Initial archive comparison treated Mac-generated AppleDouble `._Cargo.toml` as a
live source file and failed before any backup/install action. Diagnostic retained:
all34metadata entries had AppleDouble signature0005160700020000. Corrected helper
validates/skips only these archive metadata entries, comparing every real file
byte-for-byte. No source mismatch, archive modification or gate relaxation.

Fresh private evidence directory:
`~/.cache/pushtrack-dev-evidence/capacity-cli-install-0001/`.
Contains previous executable `pushtrack-before-update`, saved-config backup when
present (private0600), Cargo registry metadata backups, config/index/HEAD hashes,
executed preflight, preserved failure note, install/help/installed-PTY logs,
installation report and manual rollback command. No old evidence overwritten or
private settings published/uploaded. Root directory0700.

## Installation and checks

Existing `scripts/install.sh` run with `PREFIX=$HOME/.local`,
`CARGO_NET_OFFLINE=true`, `CARGO_NET_RETRY=0`; existing command is
`cargo install --path <worktree> --root ~/.local --force --locked`.
Cached build, successful replacement. No PATH edit/new dependencies/network call.
Installed **v0.1.0**, byte-identical to the candidate above; version not bumped.

- `command -v`, `--version`, `--help` passed.
- Full **installed-binary** PTY passed: layout/navigation, signals/restoration,
  owned fetch cleanup, staged-only edit/review/stale refusal, capacity/Enter and
  Esc decline/no automatic expansion, model/download mechanics with fake transport,
  owned descendant cleanup. No real model/download/large generation in this run.
- Config existence/content/symlink target, index/HEAD, pinned GGUF full SHA-256,
  runtime every installed file/link unchanged. Prior CLI backup identity intact.
- No remaining app/model process at final observation. No user process killed.

## Use and limits

Quit any old dashboard normally with `q`, then:

```bash
pushtrack --watch
```

`m` now reports complete staged files/bytes,4MiB cap and full-policy-prompt token
capacity when input is supported. Default4096 retained. Enter on a capacity screen
explicitly approves the recommended larger CPU context; Esc declines. Long-context
completion/accuracy/RAM remains unverified and existing300s job deadline applies.
No source is omitted/truncated and no automatic staging/committing occurs.

**Current88file staged patch still contains reserved chat/control markers.** It
fits the new byte bound but fails the unchanged control gate before weights load;
no valid token count/subject is promised. Literal-marker safety design would need
separate approval; installation does not bypass that policy.

Manual rollback only (restores prior executable, not settings/index/models):

```bash
cp "$HOME/.cache/pushtrack-dev-evidence/capacity-cli-install-0001/pushtrack-before-update" "$HOME/.local/bin/pushtrack"
```

Cargo version/prefix/source package identity unchanged across replacement. No
config/registry restoration is required just to use that backed-up executable;
original registry files remain retained for inspection. Stop after this install.
