#!/usr/bin/env bash


curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y

. ~/.bashrc

rustup update


##
## Install cargo packages
##

cargo install --locked yazi-fm yazi-cli  # cool file viewer, yazi

cargo install htmlq  # like jq but for html

sudo apt install libxcb-render0-dev libxcb-shape0-dev libxcb-xfixes0-dev
cargo install jless  # less like tool for json

cargo install difftastic  # semantic diff tool

cargo install mprocs  # allows for multiple parallel commands

