#!/usr/bin/env bash
## @extra glow | Render markdown in the terminal
set -euo pipefail

# shellcheck source=install/versions.sh
source "$(dirname "${BASH_SOURCE[0]}")/../versions.sh"

if ! command -v glow &>/dev/null; then
    tmp_deb=$(mktemp --suffix=.deb)
    curl -sLo "${tmp_deb}" \
        "https://github.com/charmbracelet/glow/releases/download/v${GLOW_VERSION}/glow_${GLOW_VERSION}_amd64.deb"
    sudo dpkg -i "${tmp_deb}"
    rm "${tmp_deb}"
else
    echo "glow is already installed on this system"
fi
