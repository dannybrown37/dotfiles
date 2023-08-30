#!/usr/bin/env bash

# Get Windows username (once) to interact with Windows side of WSL divide
if ! grep -q "^export WINDOWS_USERNAME=" "${HOME}/.bashrc"; then
    ls /mnt/c/Users
    read -p "What is your Windows username? " windows_username
    echo "export WINDOWS_USERNAME=$windows_username" >> ~/.bashrc
fi

root_dir=$(dirname $(readlink -f "${BASH_SOURCE[0]}"))

source $root_dir/bash/profile.sh  # Bash profile
source $root_dir/vscode/vsc_setup.sh  # VSCode settings.json and extensions

# autoenv automatically runs .env file when you cd in
curl -#fLo- 'https://raw.githubusercontent.com/hyperupcall/autoenv/master/scripts/install.sh' | sh

source ~/.bashrc
echo dotfiles setup complete!
