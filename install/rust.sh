#!/usr/bin/env bash
## @make 24 Languages & Runtimes | Install the Rust toolchain (rustup, latest stable)

##
## Toolchain only. `make bootstrap` depends on this because cli-tools.sh installs
## eza from crates.io, so keep it cheap -- the cargo utilities that are not core
## workflow moved to install/rust-tools.sh (`make rust-tools`).
##

curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y

# Only for the rest of *this* script -- PATH does not survive into the next Make
# target, which is why cli-tools.sh and rust-tools.sh source this too.
# shellcheck source=install/cargo_env.sh
source "$(dirname "${BASH_SOURCE[0]}")/cargo_env.sh"

rustup update
