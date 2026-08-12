#!/usr/bin/env bash
## @make 11 Start Here | Update apt and install every apt package this repo needs

##
## Split out of the old install/bash.sh. First step of `make bootstrap`, and the
## one every other install script assumes has run -- curl, wget, jq, git and gh
## all come from here, and cli-tools.sh needs jq to resolve release tags.
##
## The package list itself lives in apt_packages.sh, shared with
## scripts/dotfiles_audit.sh so the audit checks exactly what this installs.
##
# shellcheck source=install/apt_packages.sh
source "$(dirname "${BASH_SOURCE[0]}")/apt_packages.sh"

sudo apt -y update
sudo apt -y upgrade

for package in "${apt_packages[@]}"; do
    if ! dpkg -s "${package}" >/dev/null 2>&1; then
        sudo apt install -y "${package}"
    fi
done
