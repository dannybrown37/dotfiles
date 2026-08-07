#!/usr/bin/env bash

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

"${repo_dir}/scripts/install.sh"
