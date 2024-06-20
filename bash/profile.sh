#!/bin/bash

script=$(readlink -f "$BASH_SOURCE")
profile_path=$(dirname "$script")


# Use --install argument to install apt, pyenv, and npm dependencies
# should only need to use this for initial setup
if [[ $1 == "--install" ]]; then

    if [ -n "$WSL_DISTRO_NAME" ]; then  # WSL-only luxuries
        installation_order=(
            .apt_packages
            .golang_install
        )
    else  # Git Bash installs
        winget install --id koalaman.shellcheck
    fi

    installation_order+=(
        .git_init
        .npm_init
        .pipx_setup
        .curl_installs
    )

    for dotfile in "${installation_order[@]}"; do
        source $profile_path/$dotfile
    done
fi

# Source these files every time this file is run regardless of flag
profile_files=(
        .envvars
        .functions
        .aliases
        .secrets
        .aws
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
