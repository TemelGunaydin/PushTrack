#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
prefix="${PREFIX:-$HOME/.local}"

cargo install --path "$root" --root "$prefix" --force --locked
printf '\nInstalled: %s/bin/pushtrack\n' "$prefix"
printf 'Make sure %s/bin is in your PATH.\n' "$prefix"
printf '\nStart with: pushtrack add /path/to/projects\n'
printf 'Open the dashboard: pushtrack --fetch --watch\n'
