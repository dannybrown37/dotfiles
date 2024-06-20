#!/usr/bin/env bash

root_dir=$(dirname $(readlink -f "${BASH_SOURCE[0]}"))

source $root_dir/bash/profile.sh --install  # includes apt, npm, and go installs

source $root_dir/vscode/vsc_setup.sh  # VSCode settings.json and extensions

source ~/.bashrc

echo dotfiles setup complete!
