#!/usr/bin/env bash


curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y

. ~/.bashrc

rustup update


##
## Install cargo packages
##

cargo install --locked yazi-fm yazi-cli
