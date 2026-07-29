#!/usr/bin/env bash

# @doc Export a dotfiles skill into another repo (.claude + .github bridge) | skill-export <name> [target-dir]

skill-export() {
    local dotfiles_dir="${DOTFILES_DIR:-$HOME/projects/dotfiles}"
    local skill_name="${1:-}"

    if [[ -z "${skill_name}" ]]; then
        skill_name="$(find "${dotfiles_dir}/.claude/skills" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' |
            sort |
            fzf --prompt="Export which skill? " --height=40% --reverse)"

        if [[ -z "${skill_name}" ]]; then
            echo "skill-export: nothing selected" >&2
            return 1
        fi
    fi

    local source_dir="${dotfiles_dir}/.claude/skills/${skill_name}"
    if [[ ! -d "${source_dir}" ]]; then
        echo "skill-export: no such skill '${skill_name}' in ${dotfiles_dir}/.claude/skills" >&2
        return 1
    fi

    local target_dir="${2:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
    local claude_dest="${target_dir}/.claude/skills/${skill_name}"
    local github_dest="${target_dir}/.github/skills/${skill_name}"

    if [[ -e "${claude_dest}" ]]; then
        echo "skill-export: ${claude_dest} already exists, skipping copy" >&2
    else
        mkdir -p "${target_dir}/.claude/skills"
        cp -r "${source_dir}" "${claude_dest}"
        echo "Copied ${skill_name} -> ${claude_dest}"
    fi

    if [[ -e "${github_dest}" ]]; then
        echo "skill-export: ${github_dest} already exists, skipping symlink" >&2
    else
        mkdir -p "${target_dir}/.github/skills"
        ln -s "../../.claude/skills/${skill_name}" "${github_dest}"
        echo "Linked ${github_dest} -> .claude/skills/${skill_name}"
    fi
}
