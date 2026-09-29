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
## Needs apt.sh to have run: curl fetches the releases.
##
# shellcheck source=install/versions.sh
source "$(dirname "${BASH_SOURCE[0]}")/versions.sh"
# shellcheck source=install/release_binary.sh
source "$(dirname "${BASH_SOURCE[0]}")/release_binary.sh"

##
## Install just and eza (modern ls replacement) from prebuilt musl releases.
## Not in bookworm's apt.
##

install_release_binary just \
    "https://github.com/casey/just/releases/download/${JUST_VERSION}/just-${JUST_VERSION}-x86_64-unknown-linux-musl.tar.gz"
install_release_binary eza \
    "https://github.com/eza-community/eza/releases/download/v${EZA_VERSION}/eza_x86_64-unknown-linux-musl.tar.gz"

##
## Install zoxide, per creator, Debian/Ubuntu have old versions in apt
## https://github.com/ajeetdsouza/zoxide/issues/694#issuecomment-1946069618
##

install_release_binary zoxide \
    "https://github.com/ajeetdsouza/zoxide/releases/download/v${ZOXIDE_VERSION}/zoxide-${ZOXIDE_VERSION}-x86_64-unknown-linux-musl.tar.gz"

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
