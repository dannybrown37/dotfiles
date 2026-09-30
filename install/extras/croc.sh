#!/usr/bin/env bash
## @extra croc | Send files between machines securely
set -euo pipefail

if [[ ! -f "${HOME}/.local/bin/croc" ]]; then
    curl https://getcroc.schollz.com | bash
else
    echo "croc is already installed on this system"
fi
