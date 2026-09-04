#!/usr/bin/env bash
## @just 36 Developer Tools | Install GitHub stacked PR CLI extension (gh stack)

set -euo pipefail

if ! command -v gh &>/dev/null; then
    echo "gh CLI is required -- run 'make apt' first" >&2
    exit 1
fi

stack_repo=$(
    gh extension list | awk -F '\t' '$1=="gh stack"{print $2; exit}'
)

if [[ -n "${stack_repo}" ]]; then
    echo "gh stack is already provided by ${stack_repo} -- upgrading"
    gh extension upgrade "${stack_repo}"
else
    echo "Installing gh-stack extension"
    gh extension install github/gh-stack
fi

installed_version=$(
    gh extension list | awk -F '\t' '$1=="gh stack"{print $3; exit}'
)

if [[ -z "${installed_version}" ]]; then
    echo "gh-stack install failed: extension not found in gh extension list" >&2
    exit 1
fi

echo "gh-stack ${installed_version} is ready"
