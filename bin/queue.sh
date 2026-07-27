#!/usr/bin/env bash

# @doc AI work queue -- add items, discuss, track completion | queue list

_queue_py() {
    local repo_root="$1"
    shift

    uv run python "${repo_root}/scripts/queue_cli.py" \
        --queue-path "${repo_root}/.queue" \
        --complete-path "${repo_root}/.queue-complete" \
        "$@"
}

queue() {
    local repo_root
    repo_root="$(git rev-parse --show-toplevel 2>/dev/null || echo "${DOTFILES}")"

    # Titles have to match exactly, so offer them instead of retyping one.
    if [[ ("${1:-}" == "complete" || "${1:-}" == "claim") && "$*" != *--item-title* ]]; then
        local action="$1"
        local title
        title="$(_queue_py "${repo_root}" titles |
            fzf --prompt="${action^} which item? " --height=40% --reverse)"

        if [[ -z "${title}" ]]; then
            echo "queue: nothing selected" >&2
            return 1
        fi

        shift
        set -- "${action}" --item-title "${title}" "$@"
    fi

    _queue_py "${repo_root}" "$@"
}
