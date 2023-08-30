#!/usr/bin/env bash

# Get Windows username (once) to interact with Windows side of WSL divide
if ! grep -q "^export WINDOWS_USERNAME=" "${HOME}/.bashrc"; then
    ls /mnt/c/Users
    read -p "What is your Windows username? " windows_username
    echo "export WINDOWS_USERNAME=$windows_username" >> ~/.bashrc
fi

script_path=$(readlink -f "${BASH_SOURCE[0]}")
script_dir=$(dirname "$script_path")


# install apt packages
apt_packages=(
    bash-completion
    fzf
    jq
    man-db
    nodejs
    npm
    python3
    python3-distutils
)
sudo apt install -y "${apt_packages[@]}"


# install pip packages
pip install --upgrade pip
pip_packages=()
pip install "${pip_packages[@]}"


# autoenv automatically runs .env file when you cd in
curl -#fLo- 'https://raw.githubusercontent.com/hyperupcall/autoenv/master/scripts/install.sh' | sh


# "install" internal utilities by using alias >> .bashrc
bashrc_commands=(
    "alias cht=$script_dir/cht/cht.sh"
    "alias ahk=$script_dir/ahk_shortcuts/ahk.sh"
)

for command in "${bashrc_commands[@]}"; do
    if ! grep -Fxq "$command" ~/.bashrc; then
        echo "$command" >> ~/.bashrc
    fi
done


# add default bash config to ~/.bashrc
source bashrc/setup_bashrc.sh


# setup VSCode with default settings and extensions
source $script_dir/vscode/vsc_setup.sh


# source all files in path_scripts
path_scripts_dir="$script_dir/path_scripts"
if [ -d "$path_scripts_dir" ]; then
    # Loop through each script file and source it
    for script_file in "$path_scripts_dir"/*.sh; do
        if [ -f "$script_file" ]; then
            source "$script_file"
            echo "Sourced: $script_file"
        fi
    done
else
    echo "Directory '$path_scripts_dir' does not exist."
fi


source ~/.bashrc
echo Setup complete!
