#!/usr/bin/env bash
## @extra skill-tree | My Claude Code skills, hooks, and CLIs
## @mine

##
## Clone skill-tree and run its own setup
##

set -euo pipefail

repo_dir="${HOME}/projects/skill-tree"

if [[ ! -d "${repo_dir}" ]]; then
    git clone https://github.com/dannybrown37/skill-tree "${repo_dir}"
else
    echo "skill-tree already cloned at ${repo_dir}"
fi

if ! command -v uv &>/dev/null; then
    bash "$(dirname "${BASH_SOURCE[0]}")/python.sh"
    export PATH="${HOME}/.local/bin:${PATH}"
fi

"${repo_dir}/scripts/install.sh"
