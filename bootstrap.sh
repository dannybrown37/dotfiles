#!/usr/bin/env bash
set -euo pipefail

##
## The `curl | bash` entrypoint from the README: clone this repo, then hand over
## to `just bootstrap`. Library-free and header-free on purpose -- it runs
## before the repo exists, so it is not a recipe.
##
## `just` is not in Debian bookworm's apt, and cli-tools.sh installs it from
## crates.io, so on a fresh machine the three scripts that deliver it run here
## first. All three are idempotent, so bootstrap re-running them costs little.
##
## DOTFILES_DIR overrides the clone location; DOTFILES_BOOTSTRAP_RECIPE lets CI
## run its `_ci` subset through this same path.
##

readonly repo_url="https://github.com/dannybrown37/dotfiles"
readonly dotfiles_dir="${DOTFILES_DIR:-${HOME}/projects/dotfiles}"
readonly bootstrap_recipe="${DOTFILES_BOOTSTRAP_RECIPE:-bootstrap}"

# Wrapped in a function so bash parses the whole script before running any of
# it. Under `curl | bash` the script *is* stdin, and a step that reads stdin
# would otherwise swallow every line after it.
main() {
    # Give interactive steps (gh auth login, pass prompts) the terminal rather
    # than the drained pipe. There is none in CI, so only when one can be opened.
    if { : </dev/tty; } 2>/dev/null; then
        exec </dev/tty
    fi

    sudo apt update
    sudo apt install -y git

    if [[ ! -d "${dotfiles_dir}/.git" ]]; then
        mkdir -p "$(dirname "${dotfiles_dir}")"
        git clone "${repo_url}" "${dotfiles_dir}"
    fi
    cd "${dotfiles_dir}"

    if ! command -v just &>/dev/null; then
        bash install/apt.sh
        bash install/rust.sh
        bash install/cli-tools.sh
    fi
    # shellcheck source=install/cargo_env.sh
    source install/cargo_env.sh

    just "${bootstrap_recipe}"
    just
}

main "$@"
