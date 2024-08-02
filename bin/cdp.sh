#!/usr/bin/env bash

# Cd to any file in ~/projects from anywhere

# Get a list of all directories in ~/projects and store them in an array
PROJECTS_DIR="${HOME}/projects"
PROJECTS_LIST=()
while IFS= read -r -d '' dir; do
    PROJECTS_LIST+=("$(basename "${dir}")")
done < <(find "${PROJECTS_DIR}" -maxdepth 1 -type d -print0)

# Define a function to change directories and enable tab auto-completion
cdp() {
    local partial_name="$1"
    local selected_project

    # Using grep with --color=never to enable tab auto-completion
    selected_project=$(echo "${PROJECTS_LIST[@]}" | tr ' ' '\n' | grep -E --color=never "^$partial_name")

    if [[ -z "${partial_name}" ]]; then
        echo "Usage: cdp <project_name>"
    elif [[ -n "${selected_project}" ]]; then
        cd "${PROJECTS_DIR}/${selected_project}" || return
    else
        echo "Project not found."
    fi
}

# Set up bash-completion for cdp command
_cdp_completion() {
    COMPREPLY=("$(compgen -W "${PROJECTS_LIST[*]}" -- "$2")")
}
complete -F _cdp_completion cdp
