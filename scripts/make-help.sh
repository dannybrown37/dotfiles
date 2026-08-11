#!/usr/bin/env bash

##
## Generate the `make help` listing from `## @make` headers.
##
## Header format:  ## @make <order> <Section> | <description>
##
## A file in install/ becomes a Make target if and only if it carries one of
## these headers, so the target list, the .PHONY list, and this help text cannot
## drift apart -- they are all derived from the same line. `order` sorts both
## the sections and the entries within them.
##
## Targets with no install script of their own (vscode, projects, secrets-*)
## carry the header in the Makefile, directly above the target.
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

# For install scripts the filename is the target name -- that is why they are
# named after their target rather than the upstream project (spotify.sh, not
# spotify-player.sh).
install_headers() {
    awk "${parse_header}"'
        /^## @make / {
            name = FILENAME
            sub(/.*\//, "", name)
            sub(/\.(sh|ps1)$/, "", name)
            emit(substr($0, 10), name)
        }
    ' "${root}"/install/*.sh "${root}"/install/*.ps1
}

# In the Makefile the name comes from the target line the header sits above.
makefile_headers() {
    awk "${parse_header}"'
        /^## @make / { meta = substr($0, 10); next }
        meta != "" {
            if ($0 ~ /^[a-zA-Z0-9_-]+:/) {
                name = $0
                sub(/:.*/, "", name)
                emit(meta, name)
            }
            meta = ""
        }
    ' "${root}/Makefile"
}

echo "Usage: make [option]"

{
    install_headers
    makefile_headers
} | sort -t"$(printf '\t')" -k1,1n | awk -F"$(printf '\t')" '
    $2 != section { section = $2; printf "\n%s:\n", section }
    { printf "  %-16s%s\n", $3, $4 }
'
