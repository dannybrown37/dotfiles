#!/usr/bin/env bash
set -euo pipefail
## @just 43 Environment-Specific | Copy talon/ voice commands into Talon's user dir on Windows

# Copy, not symlink: Windows file watchers get no change events from \\wsl$,
# so Talon would never reload a linked folder.

if ! command -v cmd.exe &>/dev/null; then
    echo "just talon: run this from WSL with Talon installed on Windows" >&2
    exit 1
fi

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
appdata="$(wslpath "$(cd /mnt/c && cmd.exe /c 'echo %APPDATA%' | tr -d '\r')")"
user_dir="${appdata}/Talon/user"
target="${user_dir}/mine"

if [[ ! -d "${user_dir}" ]]; then
    echo "just talon: ${user_dir} not found; install Talon first" >&2
    exit 1
fi

rm -rf "${target}"
cp -r "${root}/talon" "${target}"
echo "Copied talon/ to ${target}"
