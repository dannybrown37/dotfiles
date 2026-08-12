#!/usr/bin/env bash
# shellcheck disable=SC2034

##
## Single source of truth for apt packages this repo depends on.
## Sourced by install/apt.sh (to install) and scripts/dotfiles_audit.sh (to check).
##
apt_packages=(
    asciinema
    bash-completion
    bat
    chafa
    cowsay
    curl
    faker
    fd-find
    fzf
    git
    gh
    httpie
    jq
    make
    man-db
    lolcat
    neofetch
    openssh-server
    pass
    pipx
    rename
    ripgrep
    shellcheck
    shfmt
    tldr
    tmux
    unzip
    wget
    xclip
    zip
)
