#!/usr/bin/env bash
set -euo pipefail
## Install core CLI tools that have no usable distro package

##
## Split out of the old install/bash.sh, where these sat interleaved with the
## bash profile and the password-store. Every tool here is core workflow and
## every one is the same shape: skip if already present, otherwise fetch an
## upstream release. They live together because the reason they are not just
## apt_packages entries is the same in each case -- Debian/Ubuntu either has no
## package or has one too old to be worth using.
##
## Needs apt.sh to have run: jq resolves the release tags, curl fetches them.
## eza needs cargo, so `just bootstrap` runs `rust` before this -- and cargo_env.sh
## is what actually makes that ordering count, since PATH does not cross a Make
## target boundary.
##
# shellcheck source=install/cargo_env.sh
source "$(dirname "${BASH_SOURCE[0]}")/cargo_env.sh"
# shellcheck source=install/versions.sh
source "$(dirname "${BASH_SOURCE[0]}")/versions.sh"

##
## Install eza (modern ls replacement, community fork of exa)
## Not in default Debian/Ubuntu repos, and the packaged builds lag badly --
## install from crates.io so it tracks upstream.
##

for cargo_tool in eza just; do
    if ! command -v "${cargo_tool}" &>/dev/null; then
        if command -v cargo &>/dev/null; then
            cargo install --locked "${cargo_tool}"
        else
            echo "${cargo_tool} needs cargo -- run 'just rust' then 'just _cli-tools'" >&2
        fi
    else
        echo "${cargo_tool} is already installed on this system"
    fi
done

##
## Install zoxide, per creator, Debian/Ubuntu have old versions in apt
## https://github.com/ajeetdsouza/zoxide/issues/694#issuecomment-1946069618
##

if [[ ! -f "${HOME}/.local/bin/zoxide" ]]; then
    curl -sS https://raw.githubusercontent.com/ajeetdsouza/zoxide/main/install.sh | bash
else
    echo "zoxide is already installed on this system"
fi

##
## Install delta (syntax-highlighting git pager)
##

if ! command -v delta &>/dev/null; then
    tmp_deb=$(mktemp --suffix=.deb)
    curl -sLo "${tmp_deb}" \
        "https://github.com/dandavison/delta/releases/download/${DELTA_VERSION}/git-delta_${DELTA_VERSION}_amd64.deb"
    sudo dpkg -i "${tmp_deb}"
    rm "${tmp_deb}"
else
    echo "delta already installed: $(delta --version)"
fi
