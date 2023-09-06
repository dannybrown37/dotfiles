#!/bin/bash

script=$(readlink -f "$BASH_SOURCE")
profile_path=$(dirname "$script")


# Run all dotfiles
installation_order=(
    .apt
    .functions
    .envvars
    .aliases
    .secrets
    .scripts
    .pyenv
    .npm
)

if [ $1 = "--no_installs" ]; then
    installation_order=(
        .functions
        .envvars
        .aliases
        .scripts
        .secrets
    )
fi


for dotfile in "${installation_order[@]}"; do
    touch $profile_path/$dotfile
    source $profile_path/$dotfile
done

# Add this script to .bashrc with --no_installs flag (if it's not already there)
lines_for_bash_rc=(
    "# Set up bash profile from dotfiles repo"
    "source $script --no_installs"
)
for line in "${lines_for_bash_rc[@]}"; do
    if ! grep -qF "$line" "${HOME}/.bashrc"; then
        echo $line >> "${HOME}/.bashrc"
    fi
done
