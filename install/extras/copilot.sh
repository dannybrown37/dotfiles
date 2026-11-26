#!/usr/bin/env bash
## @extra copilot | GitHub Copilot CLI coding agent
set -euo pipefail

# shellcheck source=install/curl_retry.sh
source "$(dirname "${BASH_SOURCE[0]}")/../curl_retry.sh"

## Install script rather than npm, so it does not depend on `just extras node`.
## https://github.com/github/copilot-cli

if command -v copilot &>/dev/null; then
    echo "copilot is already installed: $(copilot --version | head -1)"
else
    curl_buffered -fsSL https://gh.io/copilot-install | bash
fi
