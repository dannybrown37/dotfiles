#!/usr/bin/env bash

##
## Pick and install Windows-side tools. winget/npm/uv items come from
## install/win-dev.ps1 (-List / -Only); win32yank is the one WSL-side item.
##

set -euo pipefail

readonly EXIT_USAGE=2
readonly root="${DOTFILES_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
readonly win_dev="${root}/install/win-dev.ps1"

usage() {
    cat <<'EOF'
Usage: just windows              Pick items in a menu (✓ = installed)
       just windows <name>...    Install the named items
       just windows --all        Install everything
       just windows --list       List items and whether each is installed
EOF
}

win_path() {
    if command -v wslpath &>/dev/null; then
        wslpath -w "$1"
    else
        echo "$1"
    fi
}

win_dev() {
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$(win_path "${win_dev}")" "$@"
}

# Emits: name<TAB>installed(0/1)<TAB>description
items() {
    win_dev -List | tr -d '\r'
    local yank=0
    command -v win32yank.exe &>/dev/null && yank=1
    printf 'win32yank\t%s\tClipboard bridge for WSL\n' "${yank}"
}

list() {
    local name ok desc mark
    while IFS=$'\t' read -r name ok desc; do
        mark="·"
        [[ "${ok}" == 1 ]] && mark="✓"
        printf "%s %-12s %s\n" "${mark}" "${name}" "${desc}"
    done < <(items)
}

install() {
    local known name ps_items=() yank=""
    known="$(items | cut -f1)"
    for name in "$@"; do
        if ! grep -qxF "${name}" <<<"${known}"; then
            echo "unknown item: ${name}" >&2
            echo "available: $(tr '\n' ' ' <<<"${known}")" >&2
            exit "${EXIT_USAGE}"
        fi
    done
    for name in "$@"; do
        if [[ "${name}" == win32yank ]]; then
            yank=1
        else
            ps_items+=("${name}")
        fi
    done
    if ((${#ps_items[@]})); then
        win_dev -Only "$(
            IFS=,
            echo "${ps_items[*]}"
        )"
    fi
    if [[ -n "${yank}" ]]; then
        bash "${root}/install/win32yank.sh"
    fi
}

install_all() {
    win_dev
    bash "${root}/install/win32yank.sh"
}

pick() {
    local picked
    picked="$(list | fzf --multi --prompt='windows> ' \
        --header='TAB to select, ENTER to install' | awk '{print $2}')" || true
    [[ -n "${picked}" ]] || return 0
    mapfile -t names <<<"${picked}"
    echo "just windows ${names[*]}"
    install "${names[@]}"
}

case "${1:-}" in
-h | --help)
    usage
    exit 0
    ;;
esac

if ! command -v powershell.exe &>/dev/null; then
    echo "just windows: powershell.exe not found — run this from WSL" >&2
    exit 1
fi

case "${1:-}" in
--list)
    list
    ;;
--all)
    install_all
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
