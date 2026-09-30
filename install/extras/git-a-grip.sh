#!/usr/bin/env bash
## @extra gag | Pre-commit hooks for commit messages, docs, and tests (git-a-grip)

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
    bash "$(dirname "${BASH_SOURCE[0]}")/python.sh"
    export PATH="${HOME}/.local/bin:${PATH}"
fi

cd "${repo_dir}"
uv tool install --force --editable .
