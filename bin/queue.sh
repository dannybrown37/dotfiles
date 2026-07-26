#!/usr/bin/env bash
# Wrapper for queue.py — invoke from sourced bin/

queue() {   # @doc AI work queue — add items, discuss, track completion | queue list
    local repo_root
    repo_root="$(git rev-parse --show-toplevel 2>/dev/null || echo "${DOTFILES}")"

    uv run python "${repo_root}/scripts/queue.py" \
        --queue-path "${repo_root}/.queue" \
        --complete-path "${repo_root}/.queue-complete" \
        "$@"
}
