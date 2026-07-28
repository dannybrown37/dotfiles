#!/usr/bin/env bash

# @doc AI work queue -- add items, discuss, track completion | queue list

# queue_cli.py lives in skill-tree, not here -- this file is just the
# interactive shell/fzf glue around it.
_queue_py() {
    local skill_tree_dir="${SKILL_TREE_DIR:-${HOME}/projects/skill-tree}"
    uv run python "${skill_tree_dir}/scripts/queue_cli.py" "$@"
}

# Repo names the tag picker offers: git repos directly under $PROJECTS_DIR.
# Matches the @anchor convention scripts/secrets.sh resolves against.
_queue_repo_candidates() {
    local projects_dir="${PROJECTS_DIR:-${HOME}/projects}" dir
    for dir in "${projects_dir}"/*/; do
        [[ -e "${dir}.git" ]] && basename "${dir}"
    done
}

# fzf a value from stdin, falling back to the typed query if nothing was
# selected -- lets a repo be picked from the list or typed fresh (e.g. one
# only cloned on another machine).
_queue_pick_or_type() {
    local prompt="$1" result query choice
    result="$(fzf --prompt="${prompt} " --height=40% --reverse --print-query)"
    query="$(head -n1 <<<"${result}")"
    choice="$(sed -n 2p <<<"${result}")"
    printf '%s\n' "${choice:-${query}}"
}

queue() {
    local action="${1:-}"

    # Titles have to match exactly, so offer them instead of retyping one.
    # A tag picker sees every item (--all), since retagging a mistagged item
    # is the point; claim/complete stay scoped to the current repo.
    if [[ ("${action}" == "complete" || "${action}" == "claim" || "${action}" == "tag") &&
        "$*" != *--item-title* ]]; then
        local title extra=()
        [[ "${action}" == "tag" ]] && extra=(--all)

        title="$(_queue_py titles "${extra[@]}" |
            fzf --prompt="${action^} which item? " --height=40% --reverse)"

        if [[ -z "${title}" ]]; then
            echo "queue: nothing selected" >&2
            return 1
        fi

        shift
        set -- "${action}" --item-title "${title}" "$@"
    fi

    # Untagging (--repo "") has to be passed explicitly -- an empty fzf
    # query still matches everything, so it can't mean "no repo" here.
    if [[ "${action}" == "tag" && "$*" != *--repo* ]]; then
        local repo
        repo="$(_queue_repo_candidates | _queue_pick_or_type "Tag with which repo?")"

        if [[ -z "${repo}" ]]; then
            echo "queue: nothing selected" >&2
            return 1
        fi

        set -- "$@" --repo "${repo}"
    fi

    _queue_py "$@"
}
