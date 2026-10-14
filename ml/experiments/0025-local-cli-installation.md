# 0025 — Install the verified local CLI

2026-10-13. User requested `guncelle` after approving the actual Mac model proof.
Work stayed inline; no product code change, model inference/download, training
restart, Git commit/push, sudo, PATH/system/security modification or asset move.

## Installed state

No installed `pushtrack` was found in the current PATH or standard user/Homebrew
locations; `~/.local/bin/pushtrack` and prefix Cargo registry metadata were absent.
Therefore this was a **first local installation**, not replacement of a found old
executable. That absence is recorded, not treated as a missing backup. The verified
preinstall worktree binary is retained separately as a fallback; private saved
config existence/hash was captured without changing its contents.

`~/.local/bin` was already in PATH. Existing `scripts/install.sh` ran with
`PREFIX=$HOME/.local`, `CARGO_NET_OFFLINE=true`, `CARGO_NET_RETRY=0`:
`cargo install --path <current worktree> --root ~/.local --force --locked`.
Cached dependencies reused; no new network/provider/package runtime installation.

Installed: **`~/.local/bin/pushtrack`**, version0.1.0. Source remains the current
uncommitted worktree; version was not artificially bumped. SHA-256:
cb4416334771e53ec319c3cbee11aa5353e0434a3a2753f3be249fb3ca524f1f.
This is **byte-identical** to the binary used by the completed [actual Mac TUI
proof](0024-mac-native-drafts.md), so no extra neural/model/data test was required.

## Checks

- `command -v pushtrack` resolves exactly to the intended user prefix.
- `pushtrack --version` and `--help` passed; ai-model/server/python flags and a/m
  model/draft help present.
- Full installed-binary PTY acceptance passed on isolated synthetic fixtures:
  navigation/resize/refresh, colors, signals/raw/alternate-screen restoration,
  owned fetch cleanup, requested-only staged draft/edit/stale refusal, model/source
  selection, confirmed byte progress/cancellation/partial retention. Fake inference
  and fake curl are explicit: no actual model work or network download in this test.
- Post-test saved settings existence/hash unchanged, existing full GGUF SHA-256
  and every installed runtime file/link unchanged. No remaining model process.
- Still-current52-test/strictClippy/release and actual-model proof reused because
  installed bytes match exactly; no research/training tests or stale claims.

Evidence: `~/.cache/pushtrack-dev-evidence/local-cli-install-0001/` contains private
preinstall/config/registry state, fallback verified binary, install/help/PTY logs,
`installation-report.json`, rollback and explicit AI launch command. Private user
config backup is not added to Git or uploaded. No previous proof overwritten.

Start the dashboard: `pushtrack --watch`. `a` opens the model manager; `m` requests
staged-only drafts. Python/runtime/model configuration still explicit: installation
**did not move** the verified proof cache into default model storage or add a runtime
to PATH. The already verified setup can be launched with:

```bash
pushtrack --watch \
  --ai-model "$HOME/.cache/pushtrack-dev-evidence/model-store-0002/real-tui-acquisition-0001/cache/pushtrack/models/qwen35-4b-q4km-v2/Qwen3.5-4B-Q4_K_M.gguf" \
  --ai-server "$HOME/.cache/pushtrack/runtimes/llama-b11429-macos-arm64-0001/llama-b11429/llama-server" \
  --ai-python /opt/homebrew/bin/python3.12
```

Rollback for this newly installed CLI (do not execute automatically):

```bash
cargo uninstall --root "$HOME/.local" pushtrack
```

This removes the installed CLI through its Cargo registry; user folder settings,
models, runtime, backups/evidence and repository source remain. A launcher or
persistent AI settings require separate user approval. Code remains uncommitted/
unpushed; Linux support/performance and broad semantic model accuracy are not
established by this installation.
