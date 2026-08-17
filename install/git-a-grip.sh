#!/usr/bin/env bash
## @just 63 My Dev Tooling | Clone git-a-grip and install it with uv

##
## Clone git-a-grip and install it with uv
##

set -euo pipefail

repo_dir="${HOME}/projects/git-a-grip"

if [[ ! -d "${repo_dir}" ]]; then
    git clone https://github.com/dannybrown37/git-a-grip "${repo_dir}"
else
    echo "git-a-grip already cloned at ${repo_dir}"
fi

if ! command -v uv &>/dev/null; then
    echo "uv not found -- run 'make python' first" >&2
    exit 1
fi

cd "${repo_dir}"
uv sync
uv pip install -e .
