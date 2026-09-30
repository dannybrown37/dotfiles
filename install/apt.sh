#!/usr/bin/env bash
set -euo pipefail
## Update apt and install every apt package this repo needs

##
## Split out of the old install/bash.sh. First step of `just bootstrap`, and the
## one every other install script assumes has run -- curl, wget, jq, git and gh
## all come from here, and cli-tools.sh needs jq to resolve release tags.
##
## The package list itself lives in apt_packages.sh, shared with
## scripts/dotfiles_audit.sh so the audit checks exactly what this installs.
##
# shellcheck source=install/apt_packages.sh
source "$(dirname "${BASH_SOURCE[0]}")/apt_packages.sh"

## Debian's own gh lags years behind; GitHub's repo tracks every release, so
## the `apt install` below keeps gh current. Steps from cli/cli docs/install_linux.md.
gh_keyring=/etc/apt/keyrings/githubcli-archive-keyring.gpg
gh_apt_list="${GH_APT_LIST:-/etc/apt/sources.list.d/github-cli.list}"
if [[ ! -f "${gh_apt_list}" ]]; then
    command -v wget >/dev/null || { sudo apt -y update && sudo apt install -y wget; }
    gh_key=$(mktemp)
    wget -nv -O "${gh_key}" https://cli.github.com/packages/githubcli-archive-keyring.gpg
    sudo mkdir -p -m 755 /etc/apt/keyrings
    sudo install -m 644 "${gh_key}" "${gh_keyring}"
    rm -f "${gh_key}"
    echo "deb [arch=$(dpkg --print-architecture) signed-by=${gh_keyring}] https://cli.github.com/packages stable main" |
        sudo tee "${gh_apt_list}" >/dev/null
fi

sudo apt -y update
# Installs what is missing and upgrades what is listed -- deliberately not a
# full `apt upgrade`, which on Ubuntu pulled in the firefox snap and failed CI
# whenever the Snap Store timed out.
sudo apt install -y "${apt_packages[@]}"

## Debian stable's tmux predates 3.4, the first to pass OSC 8 hyperlinks through
## (git ship's clickable check names), so take it from backports. Ubuntu ships 3.4+.
if [[ "$(. /etc/os-release && echo "${ID}")" == debian ]]; then
    backports="$(. /etc/os-release && echo "${VERSION_CODENAME}")-backports"
    if ! apt-cache policy | grep -q " ${backports}/"; then
        echo "deb http://deb.debian.org/debian ${backports} main" |
            sudo tee "/etc/apt/sources.list.d/${backports}.list" >/dev/null
        sudo apt -y update
    fi
    sudo apt install -y -t "${backports}" tmux
fi
