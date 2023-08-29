#!/usr/bin/env bash

if ! $WINDOWS_USERNAME; then
    ls /mnt/c/Users
    read -p "What is your Windows username? " windows_username
else
    echo wtf
fi

script_path=$(readlink -f "${BASH_SOURCE[0]}")
script_dir=$(dirname "$script_path")

# install third-party utils
apt_packages=(
    bash-completion
    fzf
    man
    nodejs
    python3
)
sudo apt install -y "${apt_packages[@]}"


# autoenv automatically runs .env file when you cd in
curl -#fLo- 'https://raw.githubusercontent.com/hyperupcall/autoenv/master/scripts/install.sh' | sh


# "install" internal utilities by using alias >> .bashrc

bashrc_commands=(
    "alias cht=$script_dir/cht/cht.sh"
    "alias ahk=$script_dir/ahk_shortcuts/ahk.sh"
    "export WINDOWS_USERNAME=$windows_username"
)

for command in "${bashrc_commands[@]}"; do
    if ! grep -Fxq "$command" ~/.bashrc; then
        echo "$command" >> ~/.bashrc
    fi
done

source $script_dir/vscode/vsc_setup.sh

source ~/.bashrc
echo Internal dependencies installed
