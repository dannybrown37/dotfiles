#!/usr/bin/env bash
## @extra lazygit | TUI git client (with this repo's config)

##
## Install latest version of lazygit (skips if already current)
##

set -euo pipefail

# Follow the releases/latest redirect instead of api.github.com: the API's
# unauthenticated rate limit is shared across CI runner IPs and returns no tag.
latest_url=$(curl -fsSLI -o /dev/null -w '%{url_effective}' \
    https://github.com/jesseduffield/lazygit/releases/latest)
latest_version=${latest_url##*/v}

if [[ ! "${latest_version}" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "error: could not resolve latest lazygit version (got '${latest_url}')" >&2
    exit 1
fi

current_version=$(lazygit --version 2>/dev/null | grep -oP '(?<!git )version=\K[^,]+' || echo "none")

if [[ "${current_version}" == "${latest_version}" ]]; then
    echo "lazygit ${latest_version} already installed"
    exit 0
fi

echo "Installing lazygit ${current_version} → ${latest_version}"

tmp_dir=$(mktemp -d)
trap 'rm -rf "${tmp_dir}"' EXIT

curl -fsSLo "${tmp_dir}/lazygit.tar.gz" \
    "https://github.com/jesseduffield/lazygit/releases/download/v${latest_version}/lazygit_${latest_version}_Linux_x86_64.tar.gz"

tar -xf "${tmp_dir}/lazygit.tar.gz" -C "${tmp_dir}" lazygit
sudo install "${tmp_dir}/lazygit" /usr/local/bin/lazygit

echo "lazygit ${latest_version} installed at $(command -v lazygit)"

##
## Symlink lazygit config
##

# shellcheck source=install/link_config.sh
source "$(dirname "${BASH_SOURCE[0]}")/../link_config.sh"

dotfiles="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

link_config "${dotfiles}/config/lazygit.yml" \
    "${HOME}/.config/lazygit/config.yml"
