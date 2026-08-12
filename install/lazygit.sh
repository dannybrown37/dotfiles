#!/usr/bin/env bash
## @make 31 Developer Tools | Install lazygit TUI git client

##
## Install latest version of lazygit (skips if already current)
##

set -euo pipefail

sudo apt-get install -y -qq jq

latest_version=$(curl -s https://api.github.com/repos/jesseduffield/lazygit/releases/latest | jq -r '.tag_name' | sed 's/v//')
current_version=$(lazygit --version 2>/dev/null | grep -oP '(?<!git )version=\K[^,]+' || echo "none")

if [[ "${current_version}" == "${latest_version}" ]]; then
    echo "lazygit ${latest_version} already installed"
    exit 0
fi

echo "Installing lazygit ${current_version} → ${latest_version}"

tmp_dir=$(mktemp -d)
trap 'rm -rf "${tmp_dir}"' EXIT

curl -sLo "${tmp_dir}/lazygit.tar.gz" \
    "https://github.com/jesseduffield/lazygit/releases/download/v${latest_version}/lazygit_${latest_version}_Linux_x86_64.tar.gz"

tar -xf "${tmp_dir}/lazygit.tar.gz" -C "${tmp_dir}" lazygit
sudo install "${tmp_dir}/lazygit" /usr/local/bin/lazygit

echo "lazygit ${latest_version} installed at $(command -v lazygit)"

##
## Symlink lazygit config
##

# shellcheck source=install/link_config.sh
source "$(dirname "${BASH_SOURCE[0]}")/link_config.sh"

link_config "${HOME}/projects/dotfiles/config/lazygit.yml" \
    "${HOME}/.config/lazygit/config.yml"
