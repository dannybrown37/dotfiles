#!/bin/bash

script=$(readlink -f "$BASH_SOURCE")
profile_path=$(dirname "$script")

# Source these files every time this file is run
profile_files=(
    .envvars
    .functions
    .aliases
    .secrets
    .aws
)

for dotfile in "${profile_files[@]}"; do
    touch $profile_path/$dotfile
    source $profile_path/$dotfile
done

# All scripts in scripts/ directory must be sourced to pick up changes to them
# All scripts in that directory are called by their name without the `sh`
source $profile_path/../scripts/source_all.sh

# One time, add this script to ~/.bashrc (without --install flag)
lines_for_bash_rc=(
    "# Set up bash profile from dotfiles repo"
    "source ${script}"
)
for line in "${lines_for_bash_rc[@]}"; do
    if ! grep -qF "$line" "${HOME}/.bashrc"; then
        echo $line >> "${HOME}/.bashrc"
    fi
done

if [ -z "$WSL_DISTRO_NAME" ]; then
    cd  # on GitBash, start in ~
fi
