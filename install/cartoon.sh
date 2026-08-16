#!/usr/bin/env bash
## @make 32 Developer Tools | Install cartoon CLI and hook

##
## Install the latest version of cartoon and wire up its hook
## https://github.com/abhijitbansal/cartoon
##

set -euo pipefail

cargo install cartoon --locked

echo "cartoon $(cartoon --version | awk '{print $2}') installed at $(command -v cartoon)"

cartoon hook install
echo "cartoon hook installed"
