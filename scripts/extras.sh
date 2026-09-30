#!/usr/bin/env bash

##
## Pick and install opt-in tools from install/extras/.
##
## Header format:  ## @extra <binary> | <description>
##
## <binary> is what `command -v` looks for to mark the extra installed. A file
## in install/extras/ without the header is a helper, not an extra.
##
## A `## @runtime` line marks a language toolchain. Runtimes install before
## other extras, because some extras build with cargo or uv.
##

set -euo pipefail

readonly EXIT_USAGE=2
readonly root="${DOTFILES_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
readonly extras_dir="${root}/install/extras"

usage() {
    cat <<'EOF'
Usage: just extras              Pick extras in a menu (✓ = installed)
       just extras <name>...    Install the named extras
       just extras --list       List extras and whether each is installed
EOF
}

# Emits: name<TAB>binary<TAB>description
extras() {
    awk '
        /^## @extra / {
            name = FILENAME
            sub(/.*\//, "", name)
            sub(/\.sh$/, "", name)
            meta = substr($0, 11)
            i = index(meta, " | ")
            if (i == 0) { nextfile }
            printf "%s\t%s\t%s\n", name, substr(meta, 1, i - 1), substr(meta, i + 3)
            nextfile
        }
    ' "${extras_dir}"/*.sh
}

# gh extensions live under gh's data dir, not PATH, so ask gh for gh-* binaries
installed() {
    local binary=$1
    command -v "${binary}" &>/dev/null && return 0
    [[ "${binary}" == gh-* ]] || return 1
    gh extension list 2>/dev/null | cut -f1 | grep -qxF "gh ${binary#gh-}"
}

list() {
    local name binary desc mark
    while IFS=$'\t' read -r name binary desc; do
        mark="·"
        installed "${binary}" && mark="✓"
        printf "%s %-12s %s\n" "${mark}" "${name}" "${desc}"
    done < <(extras)
}

install() {
    local known name
    known="$(extras | cut -f1)"
    for name in "$@"; do
        if ! grep -qxF "${name}" <<<"${known}"; then
            echo "unknown extra: ${name}" >&2
            echo "available: $(tr '\n' ' ' <<<"${known}")" >&2
            exit "${EXIT_USAGE}"
        fi
    done
    local runtimes=() others=()
    for name in "$@"; do
        if grep -qx '## @runtime' "${extras_dir}/${name}.sh"; then
            runtimes+=("${name}")
        else
            others+=("${name}")
        fi
    done
    for name in "${runtimes[@]}" "${others[@]}"; do
        echo "── ${name}"
        bash "${extras_dir}/${name}.sh"
    done
}

pick() {
    local picked
    picked="$(list | fzf --multi --prompt='extras> ' \
        --header='TAB to select, ENTER to install' | awk '{print $2}')" || true
    [[ -n "${picked}" ]] || return 0
    mapfile -t names <<<"${picked}"
    echo "just extras ${names[*]}"
    install "${names[@]}"
}

case "${1:-}" in
-h | --help)
    usage
    ;;
--list)
    list
    ;;
"")
    if [[ -t 0 && -t 1 ]] && command -v fzf &>/dev/null; then
        pick
    else
        list
        echo
        usage
    fi
    ;;
*)
    install "$@"
    ;;
esac
