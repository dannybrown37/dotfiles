#!/usr/bin/env bash
## @make 32 Developer Tools | Install cartoon CLI (pinned version, no hook)

##
## Install a pinned version of cartoon (skips if already current)
## https://github.com/abhijitbansal/cartoon
##
## Deliberately does NOT run `cartoon hook install` -- that wires a
## PreToolUse hook into ~/.claude/settings.json that rewrites every
## test/build/lint command Claude Code runs. Opt into that manually
## once the tool has more mileage.
##

set -euo pipefail

cartoon_version="0.5.1"

current_version=$(cartoon --version 2>/dev/null | awk '{print $2}' || echo "none")

if [[ "${current_version}" == "${cartoon_version}" ]]; then
    echo "cartoon ${cartoon_version} already installed"
    exit 0
fi

echo "Installing cartoon ${current_version} → ${cartoon_version}"

cargo install cartoon --version "${cartoon_version}" --locked

echo "cartoon ${cartoon_version} installed at $(command -v cartoon)"
