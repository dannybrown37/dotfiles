#!/usr/bin/env bash
## @extra copilot | GitHub Copilot CLI coding agent
set -euo pipefail

## Install script rather than npm, so it does not depend on `just node`.
## https://github.com/github/copilot-cli

if command -v copilot &>/dev/null; then
    echo "copilot is already installed: $(copilot --version | head -1)"
else
    curl -fsSL https://gh.io/copilot-install | bash
fi
