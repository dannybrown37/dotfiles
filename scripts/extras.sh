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
## A `## @mine` line marks one of my own projects. On a terminal, names are
## colored by source: mine, runtime, or the install method read from the
## script (cargo, gh extension, apt). Downloads and anything else stay plain.
## NO_COLOR turns color off; FORCE_COLOR turns it on when piped.
##

set -euo pipefail

readonly EXIT_USAGE=2
readonly root="${DOTFILES_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
readonly extras_dir="${root}/install/extras"
readonly color_reset=$'\e[0m'
readonly colored_sources=(mine runtime cargo gh apt)
declare -Ar source_colors=(
    [mine]=$'\e[1;35m'
    [runtime]=$'\e[36m'
    [cargo]=$'\e[33m'
    [gh]=$'\e[34m'
    [apt]=$'\e[32m'
)

usage() {
    cat <<'EOF'
Usage: just extras              Pick extras in a menu (✓ = installed)
       just extras <name>...    Install the named extras
       just extras --list       List extras and whether each is installed
EOF
}

# Emits: name<TAB>binary<TAB>description<TAB>source
extras() {
    awk '
        function emit() {
            if (binary == "") { return }
            source = "other"
            if (mine) { source = "mine" }
            else if (runtime) { source = "runtime" }
            else if (cargo) { source = "cargo" }
            else if (gh) { source = "gh" }
            else if (apt && !download) { source = "apt" }
            printf "%s\t%s\t%s\t%s\n", name, binary, desc, source
        }
        FNR == 1 {
            emit()
            binary = ""
            mine = runtime = cargo = gh = apt = download = 0
        }
        /^## @extra / && binary == "" {
            meta = substr($0, 11)
            i = index(meta, " | ")
            if (i == 0) { nextfile }
            name = FILENAME
            sub(/.*\//, "", name)
            sub(/\.sh$/, "", name)
            binary = substr(meta, 1, i - 1)
            desc = substr(meta, i + 3)
        }
        /^## @mine$/ { mine = 1 }
        /^## @runtime$/ { runtime = 1 }
        /^[[:space:]]*#/ { next }
        /cargo install / { cargo = 1 }
        /gh extension install / { gh = 1 }
        /apt(-get)? install / { apt = 1 }
        /curl |install_release_binary / { download = 1 }
        END { emit() }
    ' "${extras_dir}"/*.sh
}

use_color() {
    [[ -z "${NO_COLOR:-}" ]] && [[ -n "${FORCE_COLOR:-}" || -t 1 ]]
}

legend() {
    use_color || return 0
    local source line=""
    for source in "${colored_sources[@]}"; do
        line+="${source_colors[${source}]}${source}${color_reset}  "
    done
    echo "${line% *}"
}

# gh extensions live under gh's data dir, not PATH, so ask gh for gh-* binaries
installed() {
    local binary=$1
    command -v "${binary}" &>/dev/null && return 0
    [[ "${binary}" == gh-* ]] || return 1
    gh extension list 2>/dev/null | cut -f1 | grep -qxF "gh ${binary#gh-}"
}

list() {
    local name binary desc source mark color reset
    while IFS=$'\t' read -r name binary desc source; do
        mark="·"
        installed "${binary}" && mark="✓"
        color="" reset=""
        if use_color && [[ -n "${source_colors[${source}]:-}" ]]; then
            color="${source_colors[${source}]}" reset="${color_reset}"
        fi
        printf "%s %s%-12s%s %s\n" "${mark}" "${color}" "${name}" "${reset}" "${desc}"
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
    local picked header='TAB to select, ENTER to install'
    local -x FORCE_COLOR=1
    use_color && header+=$'\n'"$(legend)"
    picked="$(list | fzf --multi --ansi --prompt='extras> ' \
        --header="${header}" | awk '{print $2}')" || true
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
    legend
    ;;
"")
    if [[ -t 0 && -t 1 ]] && command -v fzf &>/dev/null; then
        pick
    else
        list
        legend
        echo
        usage
    fi
    ;;
*)
    install "$@"
    ;;
esac
