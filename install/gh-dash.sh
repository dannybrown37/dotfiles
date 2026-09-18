#!/usr/bin/env bash
## Install gh-dash (terminal GitHub dashboard)

set -euo pipefail

if ! command -v gh &>/dev/null; then
    echo "gh CLI is required -- run 'make apt' first" >&2
    exit 1
fi

dash_repo=$(
    gh extension list | awk -F '\t' '$1=="gh dash"{print $2; exit}'
)

if [[ -n "${dash_repo}" ]]; then
    echo "gh dash is already provided by ${dash_repo} -- upgrading"
    gh extension upgrade "${dash_repo}"
else
    echo "Installing gh-dash extension"
    gh extension install dlvhdr/gh-dash
fi

installed_version=$(
    gh extension list | awk -F '\t' '$1=="gh dash"{print $3; exit}'
)

if [[ -z "${installed_version}" ]]; then
    echo "gh-dash install failed: extension not found in gh extension list" >&2
    exit 1
fi

echo "gh-dash ${installed_version} is ready"
