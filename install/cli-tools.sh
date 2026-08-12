#!/usr/bin/env bash
## @make 14 Start Here | Install the core CLI tools with no usable distro package

##
## Split out of the old install/bash.sh, where these sat interleaved with the
## bash profile and the password-store. Every tool here is core workflow and
## every one is the same shape: skip if already present, otherwise fetch an
## upstream release. They live together because the reason they are not just
## apt_packages entries is the same in each case -- Debian/Ubuntu either has no
## package or has one too old to be worth using.
##
## Needs apt.sh to have run: jq resolves the release tags, curl fetches them.
## eza needs cargo, so `make bootstrap` runs `rust` before this -- and cargo_env.sh
## is what actually makes that ordering count, since PATH does not cross a Make
## target boundary.
##
# shellcheck source=install/cargo_env.sh
source "$(dirname "${BASH_SOURCE[0]}")/cargo_env.sh"

##
## Install eza (modern ls replacement, community fork of exa)
## Not in default Debian/Ubuntu repos, and the packaged builds lag badly --
## install from crates.io so it tracks upstream.
##

if ! command -v eza &>/dev/null; then
    if command -v cargo &>/dev/null; then
        cargo install eza
    else
        echo "eza needs cargo -- run 'make rust' then 'make cli-tools'" >&2
    fi
else
    echo "eza is already installed on this system"
fi

##
## Install tokei (code stats) -- v12 is last release with pre-built binaries
##

if ! command -v tokei &>/dev/null; then
    tmp_dir=$(mktemp -d)
    curl -sLo "${tmp_dir}/tokei.tar.gz" \
        "https://github.com/XAMPPRocky/tokei/releases/download/v12.1.2/tokei-x86_64-unknown-linux-gnu.tar.gz"
    tar -xf "${tmp_dir}/tokei.tar.gz" -C "${tmp_dir}"
    sudo install "${tmp_dir}/tokei" /usr/local/bin/tokei
    rm -rf "${tmp_dir}"
else
    echo "tokei is already installed on this system"
fi

##
## Install hyperfine (benchmarking tool)
##

if ! command -v hyperfine &>/dev/null; then
    hf_version=$(curl -s https://api.github.com/repos/sharkdp/hyperfine/releases/latest | jq -r '.tag_name' | sed 's/v//')
    tmp_deb=$(mktemp --suffix=.deb)
    curl -sLo "${tmp_deb}" \
        "https://github.com/sharkdp/hyperfine/releases/download/v${hf_version}/hyperfine_${hf_version}_amd64.deb"
    sudo dpkg -i "${tmp_deb}"
    rm "${tmp_deb}"
else
    echo "hyperfine is already installed on this system"
fi

##
## Install glow (markdown renderer)
##

if ! command -v glow &>/dev/null; then
    glow_version=$(curl -s https://api.github.com/repos/charmbracelet/glow/releases/latest | jq -r '.tag_name' | sed 's/v//')
    tmp_deb=$(mktemp --suffix=.deb)
    curl -sLo "${tmp_deb}" \
        "https://github.com/charmbracelet/glow/releases/download/v${glow_version}/glow_${glow_version}_amd64.deb"
    sudo dpkg -i "${tmp_deb}"
    rm "${tmp_deb}"
else
    echo "glow is already installed on this system"
fi

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
    delta_version=$(curl -s https://api.github.com/repos/dandavison/delta/releases/latest | jq -r '.tag_name')
    tmp_deb=$(mktemp --suffix=.deb)
    curl -sLo "${tmp_deb}" \
        "https://github.com/dandavison/delta/releases/download/${delta_version}/git-delta_${delta_version}_amd64.deb"
    sudo dpkg -i "${tmp_deb}"
    rm "${tmp_deb}"
else
    echo "delta already installed: $(delta --version)"
fi

##
## Install croc file sharing tool
##

if [[ ! -f "${HOME}/.local/bin/croc" ]]; then
    curl https://getcroc.schollz.com | bash
else
    echo "croc is already installed on this system"
fi
