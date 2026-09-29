#!/usr/bin/env bash
## @extra fastfetch | System info summary (neofetch successor)
set -euo pipefail

## neofetch is archived upstream and gone from Debian trixie; fastfetch is
## not in bookworm's apt, so take the release .deb on both.

# shellcheck source=install/versions.sh
source "$(dirname "${BASH_SOURCE[0]}")/../versions.sh"

if ! command -v fastfetch &>/dev/null; then
    tmp_deb=$(mktemp --suffix=.deb)
    curl -sLo "${tmp_deb}" \
        "https://github.com/fastfetch-cli/fastfetch/releases/download/${FASTFETCH_VERSION}/fastfetch-linux-amd64.deb"
    sudo dpkg -i "${tmp_deb}"
    rm "${tmp_deb}"
else
    echo "fastfetch is already installed on this system"
fi
