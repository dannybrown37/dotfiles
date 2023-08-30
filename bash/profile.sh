#!/bin/bash

script=$(readlink -f "$BASH_SOURCE")
script_path=$(dirname "$script")


# Run all dotfiles
installation_order=(
    .apt
    .functions
    .envvars
    .aliases
    .scripts
    .pyenv
)

for dotfile in "${installation_order[@]}"; do
    source $script_path/$dotfile
done


# Add this script to .bashrc (if it's not already there)
lines_for_bash_rc=(
    "# Set up bash profile from dotfiles repo"
    "source $script"
)
for line in "${lines_for_bash_rc[@]}"; do
    if ! grep -qF "$line" "$user_bashrc_file"; then
        echo $line >> "${HOME}/.bashrc"
    fi
done
