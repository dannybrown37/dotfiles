#!/usr/bin/env bash

##
## Puts ~/.cargo/bin on PATH for the current script.
## Sourced by install/rust.sh, install/cli-tools.sh and install/rust-tools.sh.
##
## Library only -- no `## @just` header, so not a Make target.
##
## Needed because every Make target is its own `bash -c`, so nothing rust.sh
## does to PATH survives into the next target. The only thing that normally adds
## cargo is config/.bashrc, and a non-interactive shell never reads it. On a
## fresh machine that meant `make bootstrap` installed the toolchain in its
## `rust` step and then could not find cargo in its `cli-tools` step -- eza was
## skipped, with rust sitting right there installed. Ordering the composite
## correctly is necessary but not sufficient; each cargo-using script has to
## find cargo itself.
##

# shellcheck disable=SC1091  # written by the rustup installer, absent until then
[[ -f "${HOME}/.cargo/env" ]] && source "${HOME}/.cargo/env"

# The `&&` above is the last command when the file is missing, which would make
# a sourcing script's $? non-zero under `set -e`. Swallow it.
true
