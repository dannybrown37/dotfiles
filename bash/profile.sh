#!/bin/bash

script=$(readlink -f "$BASH_SOURCE")
profile_path=$(dirname "$script")


# Use --install argument to install apt, pyenv, and npm dependencies
if [[ $1 == "--install" ]]; then
    installation_order=(
        .apt
        .npm
    )

    for dotfile in "${installation_order[@]}"; do
        source $profile_path/$dotfile
    done
fi


# Source these files every time this file is run regardless of flag
profile_files=(
    .envvars
    .functions
    .pyenv
    .aliases
    .scripts
    .secrets
)

for dotfile in "${profile_files[@]}"; do
    touch $profile_path/$dotfile
    source $profile_path/$dotfile
done


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
