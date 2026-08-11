#!/usr/bin/env bash

##
## Single source of truth for creating config symlinks.
## Sourced by install/bash.sh, install/lazygit.sh and install/spotify.sh.
##
## Every caller used to hand-roll its own `ln -s`, and the ones in bash.sh had no
## guard at all -- a second run failed with "File exists", and because the call
## was `ln -s ... && echo`, the confirmation was skipped while the script carried
## on. Re-running looked like a no-op and was actually a pile of errors.
##
## Deliberately refuses to replace a real file or directory: a bare `ln -sf`
## would eat a hand-written ~/.gitconfig with no warning. Only symlinks -- which
## this repo is the one thing that creates -- are ever overwritten.
##

link_config() {
    local src="$1"
    local dest="$2"

    if [[ ! -e "${src}" ]]; then
        echo "link_config: source does not exist: ${src}" >&2
        return 1
    fi

    mkdir -p "$(dirname "${dest}")"

    if [[ -L "${dest}" ]]; then
        if [[ "$(readlink -f "${dest}")" == "$(readlink -f "${src}")" ]]; then
            echo "${dest} already symlinked"
            return 0
        fi
        # -n so a dest that is a symlink-to-directory is replaced, not written into
        ln -sfn "${src}" "${dest}"
        echo "Re-pointed ${dest} -> ${src}"
        return 0
    fi

    if [[ -e "${dest}" ]]; then
        echo "link_config: ${dest} exists and is not a symlink -- left alone" >&2
        return 1
    fi

    ln -s "${src}" "${dest}"
    echo "Symlinked ${dest} -> ${src}"
}
