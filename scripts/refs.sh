#!/usr/bin/env bash

set -euo pipefail

readonly EXIT_USAGE=2
readonly REFS_VERSION="0.5.0"
readonly SELF="$(realpath "${BASH_SOURCE[0]}")"
readonly DOTFILES_ROOT="$(dirname "$(dirname "${SELF}")")"

usage() {
    cat >&2 <<EOF
Usage: refs                     Pick a reference, then read it in glow
       refs <ref>               Read a reference in glow
       refs links <ref>         Pick a link (enter: open, ctrl-y: copy URL)
       refs edit <ref>          Open a reference in \$EDITOR
       refs add <ref> [<title> <description> <url>]
                                Append an entry (prompts for missing fields)
       refs files               Print the available <ref> names
       refs list <ref>          Print "index<TAB>title" per ## entry
       refs url <ref> <n>       Print the first link URL in entry n
       refs --version

<ref> is a path to a .md file, or one of: $(list_files | paste -sd ' ')
EOF
    exit "${EXIT_USAGE}"
}

markdown_in() {
    local file
    for file in "$1"/*.md; do
        [[ -f "${file}" ]] && echo "${file}"
    done
    return 0
}

# REFS_DIR narrows the search to one directory (used by the tests)
ref_paths() {
    if [[ -n "${REFS_DIR:-}" ]]; then
        markdown_in "${REFS_DIR}"
        return 0
    fi
    markdown_in "${DOTFILES_ROOT}/references"
    markdown_in "${DOTFILES_ROOT}/wsl"
    echo "${DOTFILES_ROOT}/docs/git-workflow.md"
}

list_files() {
    local file
    while IFS= read -r file; do
        basename "${file}" .md
    done < <(ref_paths)
}

resolve_file() {
    local file
    if [[ -f "$1" ]]; then
        echo "$1"
        return 0
    fi
    while IFS= read -r file; do
        if [[ "$(basename "${file}" .md)" == "$1" ]]; then
            echo "${file}"
            return 0
        fi
    done < <(ref_paths)
    usage
}

list_entries() {
    awk '/^## / { n++; printf "%d\t%s\n", n, substr($0, 4) }' "$1"
}

entry_url() {
    awk -v want="$2" '/^## / { n++ } n == want' "$1" \
        | grep -oP '\]\(\Khttps?://[^)]+' | head -n1 || true
}

copy_to_clipboard() {
    if command -v clip.exe &>/dev/null; then
        clip.exe
    else
        xclip -selection clipboard
    fi
}

open_entry() {
    local url
    url="$(entry_url "$1" "$2")"
    [[ -n "${url}" ]] || return 0
    # shellcheck source=../bin/browser.sh
    . "${DOTFILES_ROOT}/bin/browser.sh"
    open_url_in_browser "${url}" &>/dev/null
}

add_entry() {
    local file="$1" title="${2:-}" desc="${3:-}" url="${4:-}"
    if [[ $# -eq 1 ]]; then
        [[ -t 0 ]] || usage
        read -rp 'Title: ' title
        read -rp 'Description: ' desc
        read -rp 'URL: ' url
    fi
    [[ -n "${title}" && "${url}" =~ ^https?:// ]] || usage
    printf '\n## %s\n%s\n[%s](%s)\n' "${title}" "${desc}" "${title}" "${url}" >>"${file}"
    echo "Added \"${title}\" to ${file}"
}

view() {
    if [[ -t 1 ]] && command -v glow &>/dev/null; then
        glow -p "$1"
    else
        cat "$1"
    fi
}

preview() {
    if command -v glow &>/dev/null; then
        glow -s dark -w "${FZF_PREVIEW_COLUMNS:-80}" "$1"
    else
        cat "$1"
    fi
}

pick_ref() {
    list_files | fzf \
        --prompt='refs> ' --no-input \
        --reverse --height=90% \
        --header='↑/↓: pick · j/k: scroll · ctrl-d/u: page · enter: read · esc: quit' \
        --preview="'${SELF}' preview {}" \
        --preview-window='right,70%,wrap' \
        --bind='j:preview-down,k:preview-up' \
        --bind='ctrl-d:preview-half-page-down,ctrl-u:preview-half-page-up'
}

pick_link() {
    local file="$1"
    list_entries "${file}" | fzf \
        --prompt="$(basename "${file}" .md) links> " \
        --delimiter=$'\t' --with-nth=2 \
        --reverse --height=40% \
        --header='enter: open · ctrl-y: copy URL · esc: quit' \
        --bind="enter:execute-silent('${SELF}' open '${file}' {1})" \
        --bind="ctrl-y:execute-silent('${SELF}' url '${file}' {1} | tr -d '\n' | '${SELF}' copy)" \
        || true
}

main() {
    local cmd="${1:-}"
    case "${cmd}" in
    --version) echo "refs ${REFS_VERSION}"; return 0 ;;
    copy) copy_to_clipboard; return 0 ;;
    files) list_files; return 0 ;;
    links | list | url | open | edit | add | preview) shift ;;
    -h | --help) usage ;;
    "")
        [[ -t 0 && -t 1 ]] || usage
        local ref
        ref="$(pick_ref)" || return 0
        view "$(resolve_file "${ref}")"
        echo "Run again with: refs ${ref}"
        return 0
        ;;
    *) [[ $# -eq 1 ]] || usage; cmd=view ;;
    esac

    local file
    file="$(resolve_file "${1:-}")"
    case "${cmd}" in
    view) view "${file}" ;;
    preview) preview "${file}" ;;
    list) list_entries "${file}" ;;
    edit)
        [[ -t 0 && -t 1 ]] || usage
        "${EDITOR:-nvim}" "${file}"
        ;;
    add)
        [[ $# -eq 1 || $# -eq 4 ]] || usage
        add_entry "${file}" "${@:2}"
        ;;
    links)
        [[ -t 0 && -t 1 ]] || usage
        pick_link "${file}"
        ;;
    url | open)
        [[ "${2:-}" =~ ^[0-9]+$ ]] || usage
        if [[ "${cmd}" == url ]]; then
            entry_url "${file}" "$2"
        else
            open_entry "${file}" "$2"
        fi
        ;;
    esac
}

main "$@"
