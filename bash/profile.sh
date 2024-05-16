#!/bin/bash

script=$(readlink -f "$BASH_SOURCE")
profile_path=$(dirname "$script")


# Use --install argument to install apt, pyenv, and npm dependencies
# should only need to use this for initial setup
if [[ $1 == "--install" ]]; then

    if [ -n "$WSL_DISTRO_NAME" ]; then
        installation_order=(
            .apt_packages
            .git_init
            .npm_init
            .golang_install
        )
    else  # Git Bash has fewer luxuries
        installation_order=(
            .git_init
            .npm_init
        )
    fi


    for dotfile in "${installation_order[@]}"; do
        source $profile_path/$dotfile
    done

    pipx install poetry
fi

# Source these files every time this file is run regardless of flag
profile_files=(
        .envvars
        .functions
        .aliases
        .secrets
    )

# Add WSL-specific luxuries like pyenv and Go
if [ -n "$WSL_DISTRO_NAME" ]; then
    profile_files+=(
        .language_config
    )
fi

for dotfile in "${profile_files[@]}"; do
    touch $profile_path/$dotfile
    source $profile_path/$dotfile
done

# all scripts in scripts/ directory must be sourced to pick up changes
source $profile_path/../scripts/source_all.sh

ahk

# One time, add this script to ~/.bashrc (without --install flag)
lines_for_bash_rc=(
    "# Set up bash profile from dotfiles repo"
    "source $script"
)
for line in "${lines_for_bash_rc[@]}"; do
    if ! grep -qF "$line" "${HOME}/.bashrc"; then
        echo $line >> "${HOME}/.bashrc"
    fi
done

if [ -z "$WSL_DISTRO_NAME" ]; then
    cd  # on GitBash, start in ~
fi
