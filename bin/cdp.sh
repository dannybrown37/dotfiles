#!/usr/bin/env bash

# @doc Cd to any project directory from anywhere (with tab autocomplete)

PROJECTS_DIR="${HOME}/projects"
PROJECTS_LIST=()
_projects_loaded=0

_load_projects_list() {
    [[ $_projects_loaded -eq 1 ]] && return
    PROJECTS_LIST=()
    for dir in "${PROJECTS_DIR}"/*/; do
        [[ -d "$dir" ]] && PROJECTS_LIST+=("$(basename "$dir")")
    done
    _projects_loaded=1
}

cdp() {
    _load_projects_list
    local partial_name="$1"
    local selected_project

    selected_project=$(printf '%s\n' "${PROJECTS_LIST[@]}" \
        | grep -E --color=never "^${partial_name}")

    if [[ -z "${partial_name}" ]]; then
        echo "Usage: cdp <project_name>"
    elif [[ -n "${selected_project}" ]]; then
        cd "${PROJECTS_DIR}/${selected_project}" || return
    else
        echo "Project not found."
    fi
}

_cdp_completion() {
    _load_projects_list
    COMPREPLY=("$(compgen -W "${PROJECTS_LIST[*]}" -- "$2")")
}
complete -F _cdp_completion cdp
