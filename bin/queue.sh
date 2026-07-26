#!/usr/bin/env bash

# @doc AI work queue -- add items, discuss, track completion | queue list

_queue_py() {
    local repo_root="$1"
    shift

    uv run python "${repo_root}/scripts/queue.py" \
        --queue-path "${repo_root}/.queue" \
        --complete-path "${repo_root}/.queue-complete" \
        "$@"
}

queue() {
    local repo_root
    repo_root="$(git rev-parse --show-toplevel 2>/dev/null || echo "${DOTFILES}")"

    # Titles have to match exactly, so offer them instead of retyping one.
    if [[ "${1:-}" == "complete" && "$*" != *--item-title* ]]; then
        local title
        title="$(_queue_py "${repo_root}" titles |
            fzf --prompt='Complete which item? ' --height=40% --reverse)"

        if [[ -z "${title}" ]]; then
            echo "queue: nothing selected" >&2
            return 1
        fi

        shift
        set -- complete --item-title "${title}" "$@"
    fi

    _queue_py "${repo_root}" "$@"
}
