#!/usr/bin/env bash
set -euo pipefail
## @just 24 Languages & Runtimes | Install the Rust toolchain (rustup, latest stable)

##
## Toolchain only, and not part of `just bootstrap` -- core tools come from
## prebuilt releases. The cargo extras in install/extras/ need this first.
##

curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y

# Only for the rest of *this* script -- PATH does not survive into the next Make
# target, which is why the cargo extras source this too.
# shellcheck source=install/cargo_env.sh
source "$(dirname "${BASH_SOURCE[0]}")/cargo_env.sh"

rustup update
