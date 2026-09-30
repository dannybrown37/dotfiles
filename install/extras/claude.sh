#!/usr/bin/env bash
## @extra claude | Claude Code, Anthropic's coding agent CLI
set -euo pipefail

## Native installer: lands in ~/.local/bin and auto-updates itself.
## https://code.claude.com/docs/en/setup

if command -v claude &>/dev/null; then
    echo "claude is already installed: $(claude --version)"
else
    curl -fsSL https://claude.ai/install.sh | bash
fi
