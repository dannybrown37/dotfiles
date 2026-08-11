#!/usr/bin/env bash
## @make 63 My Projects | Clone ccgarden and install it with uv

##
## Clone ccgarden and install it with uv
##
## NOTE: ccgarden isn't pushed to GitHub yet as of writing -- push it to
## https://github.com/dannybrown37/ccgarden before running this.
##

set -euo pipefail

repo_dir="${HOME}/projects/ccgarden"

if [[ ! -d "${repo_dir}" ]]; then
    git clone https://github.com/dannybrown37/ccgarden "${repo_dir}"
else
    echo "ccgarden already cloned at ${repo_dir}"
fi

if ! command -v uv &>/dev/null; then
    echo "uv not found -- run 'make python' first" >&2
    exit 1
fi

cd "${repo_dir}"
uv sync
uv pip install -e .
