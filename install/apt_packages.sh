#!/usr/bin/env bash
# shellcheck disable=SC2034

##
## Single source of truth for apt packages this repo depends on.
## Sourced by install/apt.sh (to install) and scripts/dotfiles_audit.sh (to check).
##
apt_packages=(
    bash-completion
    bat
    curl
    fd-find
    fzf
    git
    gh
    jq
    make
    man-db
    openssh-server
    pass
    pipx
    rename
    ripgrep
    shellcheck
    shfmt
    tmux
    unzip
    wget
    xclip
    zip
)
