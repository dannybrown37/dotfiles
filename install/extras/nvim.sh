#!/usr/bin/env bash
set -euo pipefail
## @extra nvim | Neovim editor

# shellcheck source=install/versions.sh
source "$(dirname "${BASH_SOURCE[0]}")/../versions.sh"

##
## make and gcc build telescope-fzf-native and LuaSnip's jsregexp; without them
## both plugins skip their build silently.
##

sudo apt install -y build-essential

##
## Install Neovim from the release tarball into /opt/nvim. Older installs
## extracted the AppImage to /squashfs-root; replace those.
##

current_version=$(nvim --version 2>/dev/null | head -1 | awk '{print $2}' || true)

if [[ "${current_version}" == "v${NVIM_VERSION}" ]]; then
    echo "Neovim ${current_version} already installed"
else
    echo "Installing Neovim ${current_version:-none} → v${NVIM_VERSION}"
    tmp_dir=$(mktemp -d)
    trap 'rm -rf "${tmp_dir}"' EXIT
    curl -fsSLo "${tmp_dir}/nvim.tar.gz" \
        "https://github.com/neovim/neovim/releases/download/v${NVIM_VERSION}/nvim-linux-x86_64.tar.gz"
    sudo rm -rf /opt/nvim /squashfs-root
    if [[ "$(readlink /usr/bin/nvim || true)" == /squashfs-root/* ]]; then
        sudo rm /usr/bin/nvim
    fi
    sudo mkdir -p /opt/nvim
    sudo tar -xzf "${tmp_dir}/nvim.tar.gz" -C /opt/nvim --strip-components=1
    sudo ln -sfn /opt/nvim/bin/nvim /usr/local/bin/nvim # allow-raw-symlink: root-owned PATH entry, not a config link
    nvim --version | head -1
fi
