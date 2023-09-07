#!/usr/bin/env bash

root_dir=$(dirname $(readlink -f "${BASH_SOURCE[0]}"))

source $root_dir/bash/profile.sh --install  # Bash profile with installations
source $root_dir/vscode/vsc_setup.sh  # VSCode settings.json and extensions

# autoenv automatically runs .env file when you cd in
curl -#fLo- 'https://raw.githubusercontent.com/hyperupcall/autoenv/master/scripts/install.sh' | sh

# install pyenv
curl -L https://raw.githubusercontent.com/pyenv/pyenv-installer/master/bin/pyenv-installer | bash

source ~/.bashrc

echo dotfiles setup complete!
