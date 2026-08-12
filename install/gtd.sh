#!/usr/bin/env bash
## @make 62 My Dev Tooling | Clone gtd and install it with uv

##
## Clone gtd and install it with uv
##

set -euo pipefail

repo_dir="${HOME}/projects/gtd"

if [[ ! -d "${repo_dir}" ]]; then
    git clone https://github.com/dannybrown37/gtd "${repo_dir}"
else
    echo "gtd already cloned at ${repo_dir}"
fi

if ! command -v uv &>/dev/null; then
    echo "uv not found -- run 'make python' first" >&2
    exit 1
fi

cd "${repo_dir}"
uv sync
uv pip install -e .
