#!/usr/bin/env bash

root_dir=$(dirname $(readlink -f "${BASH_SOURCE[0]}"))

source $root_dir/bash/profile.sh --install  # includes apt, npm, and go installs

source $root_dir/vscode/vsc_setup.sh  # VSCode settings.json and extensions

# autoenv automatically runs .env file when you cd in
curl -#fLo- 'https://raw.githubusercontent.com/hyperupcall/autoenv/master/scripts/install.sh' | sh

# install nvm
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash

# install pyenv
curl -L https://raw.githubusercontent.com/pyenv/pyenv-installer/master/bin/pyenv-installer | bash

# install rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y

source ~/.bashrc

echo dotfiles setup complete!
