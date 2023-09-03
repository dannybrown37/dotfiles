#!/bin/bash

script=$(readlink -f "$BASH_SOURCE")
script_path=$(dirname "$script")


# Run all dotfiles
installation_order=(
    .apt
    .functions
    .envvars
    .aliases
    .secrets
    .scripts
    .pyenv
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

touch $script_path/.secrets

for dotfile in "${installation_order[@]}"; do
    source $script_path/$dotfile
done


# Add this script to .bashrc (if it's not already there)
lines_for_bash_rc=(
    "# Set up bash profile from dotfiles repo"
    "source $script --no_installs"
)
for line in "${lines_for_bash_rc[@]}"; do
    if ! grep -qF "$line" "${HOME}/.bashrc"; then
        echo $line >> "${HOME}/.bashrc"
    fi
done
