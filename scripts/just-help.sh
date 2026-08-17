#!/usr/bin/env bash

##
## Generate the help listing from `## @just` headers.
##
## Header format:  ## @just <order> <Section> | <description>
##
## A file in install/ becomes a recipe if and only if it carries one of
## these headers, so the recipe list and this help text cannot drift apart --
## they are both derived from the same line. `order` sorts both the sections
## and the entries within them.
##
## Recipes with no install script of their own (vscode, projects, secrets-*)
## carry the header in the justfile, directly above the recipe.
##

set -euo pipefail

readonly root="${DOTFILES_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"

readonly parse_header='
    function emit(meta, name,    i, head, desc, order, section) {
        i = index(meta, " | ")
        if (i == 0) { return }
        head = substr(meta, 1, i - 1)
        desc = substr(meta, i + 3)
        order = head
        sub(/ .*/, "", order)
        section = head
        sub(/^[0-9]+ +/, "", section)
        printf "%s\t%s\t%s\t%s\n", order, section, name, desc
    }
'

install_headers() {
    awk "${parse_header}"'
        /^## @just / {
            name = FILENAME
            sub(/.*\//, "", name)
            sub(/\.(sh|ps1)$/, "", name)
            emit(substr($0, 10), name)
        }
    ' "${root}"/install/*.sh "${root}"/install/*.ps1
}

justfile_headers() {
    awk "${parse_header}"'
        /^## @just / { meta = substr($0, 10); next }
        meta != "" {
            if ($0 ~ /^[a-zA-Z0-9_-]+:/) {
                name = $0
                sub(/:.*/, "", name)
                emit(meta, name)
            }
            meta = ""
        }
    ' "${root}/justfile"
}

echo "Usage: make [option]"

{
    install_headers
    justfile_headers
} | sort -t"$(printf '\t')" -k1,1n | awk -F"$(printf '\t')" '
    $2 != section { section = $2; printf "\n%s:\n", section }
    { printf "  %-16s%s\n", $3, $4 }
'
