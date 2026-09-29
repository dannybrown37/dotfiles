#!/usr/bin/env bash
set -euo pipefail
## @just 24 Languages & Runtimes | Install the Rust toolchain (rustup, latest stable)

##
## Toolchain only. `just bootstrap` depends on this because cli-tools.sh installs
## eza from crates.io, so keep it cheap -- the cargo utilities that are not core
## workflow moved to install/extras/ (`just extras`).
##

curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y

# Only for the rest of *this* script -- PATH does not survive into the next Make
# target, which is why cli-tools.sh and the cargo extras source this too.
# shellcheck source=install/cargo_env.sh
source "$(dirname "${BASH_SOURCE[0]}")/cargo_env.sh"

rustup update
