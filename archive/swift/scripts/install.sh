#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root"

# On macOS, use the compiler that matches the selected Xcode SDK.
if [[ "$(uname -s)" == "Darwin" ]]; then
  swift=(xcrun swift)
else
  swift=(swift)
fi

"${swift[@]}" build -c release
bin_path="$("${swift[@]}" build -c release --show-bin-path)"
prefix="${PREFIX:-$HOME/.local}"
mkdir -p "$prefix/bin"
install -m 755 "$bin_path/pushtrack" "$prefix/bin/pushtrack"
printf '\nInstalled: %s/bin/pushtrack\n' "$prefix"
printf 'Make sure %s/bin is in your PATH.\n' "$prefix"
printf '\nStart with: pushtrack add /path/to/projects\n'
