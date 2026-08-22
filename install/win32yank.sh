#!/usr/bin/env bash
## @just 41 Environment-Specific | Install win32yank clipboard bridge (WSL only)

set -euo pipefail

if [[ -z "${ON_WINDOWS:-}" ]]; then
    echo "win32yank is only needed on WSL — skipping"
    exit 0
fi

readonly VERSION="0.1.1"

current_version=$(win32yank.exe --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' || echo "none")

if [[ "${current_version}" == "${VERSION}" ]]; then
    echo "win32yank ${VERSION} already installed"
    exit 0
fi

echo "Installing win32yank ${current_version} → ${VERSION}"

tmp_dir=$(mktemp -d)
trap 'rm -rf "${tmp_dir}"' EXIT

curl -sLo "${tmp_dir}/win32yank.zip" \
    "https://github.com/equalsraf/win32yank/releases/download/v${VERSION}/win32yank-x64.zip"

unzip -q "${tmp_dir}/win32yank.zip" -d "${tmp_dir}"
chmod +x "${tmp_dir}/win32yank.exe"
sudo install "${tmp_dir}/win32yank.exe" /usr/local/bin/win32yank.exe

echo "win32yank ${VERSION} installed at $(command -v win32yank.exe)"
