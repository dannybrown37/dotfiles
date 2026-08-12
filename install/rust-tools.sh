#!/usr/bin/env bash
## @make 36 Developer Tools | Install the optional cargo utilities (htmlq, jless, difftastic, mprocs)

##
## Separated out of install/rust.sh so `make bootstrap` can depend on the Rust
## toolchain without building four crates that are not core workflow. Nothing
## else depends on these; they are here rather than deleted so the install
## recipe is not lost.
##
## Needs cargo -- run `make rust` first.
##
# shellcheck source=install/cargo_env.sh
source "$(dirname "${BASH_SOURCE[0]}")/cargo_env.sh"

if ! command -v cargo &>/dev/null; then
    echo "rust-tools needs cargo -- run 'make rust' first" >&2
    # The Makefile sources its targets, so `return` is the correct exit; `|| exit`
    # covers being run as `bash install/rust-tools.sh`, where a top-level
    # `return` is an error.
    # shellcheck disable=SC2317  # reachable when executed rather than sourced
    return 1 2>/dev/null || exit 1
fi

cargo install htmlq # like jq but for html

# jless links against libxcb for clipboard support
sudo apt install -y libxcb-render0-dev libxcb-shape0-dev libxcb-xfixes0-dev
cargo install jless # less-like tool for json

cargo install difftastic # semantic diff tool

cargo install mprocs # allows for multiple parallel commands
