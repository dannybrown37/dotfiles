#!/usr/bin/env bash
## @extra gtd | GTD CLI powered by Notion
## @mine

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
    bash "$(dirname "${BASH_SOURCE[0]}")/python.sh"
    export PATH="${HOME}/.local/bin:${PATH}"
fi

cd "${repo_dir}"
uv tool install --force --editable .
