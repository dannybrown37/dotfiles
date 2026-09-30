#!/usr/bin/env bash

set -euo pipefail

readonly EXIT_USAGE=2

usage() {
    cat <<'EOF'
Usage: just vscode                  Pick extensions in a menu (✓ = installed)
       just vscode <extension>...   Install the named extensions
       just vscode --all            Install every missing extension
       just vscode --list           List extensions and whether each is installed
       just vscode --uninstall      Uninstall every extension
EOF
}

extensions_to_install=(
    # visual/dev improvements
    aaron-bond.better-comments
    antiantisepticeye.vscode-color-picker
    eamodio.gitlens
    equinusocio.vsc-material-theme-icons
    johnpapa.vscode-peacock
    oderwat.indent-rainbow
    streetsidesoftware.code-spell-checker
    tyriar.vscode-terminal-here
    usernamehw.errorlens
    yonasvalentinmougaardkristensen.errorclipper

    # command-palette tools
    alefragnani.bookmarks
    donjayamanne.githistory

    # python
    charliermarsh.ruff
    elagil.pre-commit-helper
    jannchie.ruff-ignore-explainer
    mgesbert.indent-nested-dictionary
    ms-python.python
    ms-python.vscode-pylance

    # bash
    timonwong.shellcheck

    # js/ts
    dbaeumer.vscode-eslint
    esbenp.prettier-vscode
    orta.vscode-jest
    yoavbls.pretty-ts-errors

    # markdown and protocols
    DavidAnson.vscode-markdownlint
    mechatroner.rainbow-csv
    ms-vscode.makefile-tools
    redhat.vscode-yaml
    shd101wyy.markdown-preview-enhanced
    tamasfe.even-better-toml
    zainchen.json

    # infrastructure
    42crunch.vscode-openapi
    github.vscode-github-actions

    # jupyter
    ms-toolsai.jupyter

    # autocompletion, llms, etc.
    christian-kohler.path-intellisense
    VisualStudioExptTeam.vscodeintellicode
    VisualStudioExptTeam.vscodeintellicode-completions
    codeium.codeium
)

wanted() {
    printf '%s\n' "${extensions_to_install[@]}"
}

# VS Code may report IDs in a different case than the marketplace
installed_extensions="$(code --list-extensions | tr '[:upper:]' '[:lower:]')"

is_installed() {
    grep -qxF "${1,,}" <<<"${installed_extensions}"
}

list() {
    local id mark
    while read -r id; do
        mark="·"
        is_installed "${id}" && mark="✓"
        printf "%s %s\n" "${mark}" "${id}"
    done < <(wanted)
}

install() {
    local id
    for id in "$@"; do
        if ! wanted | grep -qxF "${id}"; then
            echo "unknown extension: ${id}" >&2
            exit "${EXIT_USAGE}"
        fi
    done
    for id in "$@"; do
        if is_installed "${id}"; then
            echo "✓ ${id} already installed"
        else
            echo "Installing extension: ${id}"
            code --install-extension "${id}"
        fi
    done
}

pick() {
    local picked
    picked="$(list | fzf --multi --prompt='vscode> ' \
        --header='TAB to select, ENTER to install' | awk '{print $2}')" || true
    [[ -n "${picked}" ]] || return 0
    mapfile -t ids <<<"${picked}"
    echo "just vscode ${ids[*]}"
    install "${ids[@]}"
}

case "${1:-}" in
-h | --help)
    usage
    ;;
--list)
    list
    ;;
--all)
    mapfile -t ids < <(wanted)
    install "${ids[@]}"
    ;;
--uninstall)
    code --list-extensions | xargs -L 1 code --uninstall-extension
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
