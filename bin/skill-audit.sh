#!/usr/bin/env bash

# @doc Audit dotfiles skills against their ~/.claude/skills copies, and sync them | skill-audit [sync] [name] [--yes]

skill-audit() {
    local dotfiles_dir="${DOTFILES_DIR:-$HOME/projects/dotfiles}"
    local global_skills_dir="${CLAUDE_GLOBAL_SKILLS_DIR:-$HOME/.claude/skills}"
    local skills_dir="${dotfiles_dir}/.claude/skills"

    local mode="check"
    local target=""
    local auto_yes=0
    local arg
    for arg in "$@"; do
        case "${arg}" in
        sync) mode="sync" ;;
        --yes | -y) auto_yes=1 ;;
        *) target="${arg}" ;;
        esac
    done

    if [[ ! -d "${skills_dir}" ]]; then
        echo "skill-audit: no such directory ${skills_dir}" >&2
        return 1
    fi

    local name source_dir global_dest resolved
    local missing=() stale=()

    for source_dir in "${skills_dir}"/*/; do
        [[ -d "${source_dir}" ]] || continue
        name="$(basename "${source_dir}")"
        [[ -n "${target}" && "${name}" != "${target}" ]] && continue

        global_dest="${global_skills_dir}/${name}"

        if [[ ! -e "${global_dest}" ]]; then
            missing+=("${name}")
            echo "MISSING   ${name}  (not exported to ${global_dest})"
        elif [[ -L "${global_dest}" ]]; then
            resolved="$(readlink -f "${global_dest}")"
            if [[ "${resolved}" == "$(readlink -f "${source_dir%/}")" ]]; then
                echo "OK        ${name}  (symlinked to repo)"
            else
                echo "EXTERNAL  ${name}  (symlink -> ${resolved}, not this repo -- skipped)"
            fi
        elif diff -rq "${source_dir%/}" "${global_dest}" >/dev/null 2>&1; then
            echo "OK        ${name}  (in sync)"
        else
            stale+=("${name}")
            echo "STALE     ${name}  (differs from repo)"
            diff -rq "${source_dir%/}" "${global_dest}" 2>/dev/null | sed 's/^/            /'
        fi
    done

    echo ""
    local global_entry gname
    for global_entry in "${global_skills_dir}"/*/; do
        [[ -e "${global_entry}" ]] || continue
        gname="$(basename "${global_entry}")"
        [[ -n "${target}" && "${gname}" != "${target}" ]] && continue
        [[ -d "${skills_dir}/${gname}" ]] && continue

        if [[ -L "${global_entry%/}" ]]; then
            echo "EXTERNAL  ${gname}  (symlink -> $(readlink -f "${global_entry%/}"), not from this repo)"
        else
            echo "ORPHAN    ${gname}  (in ${global_skills_dir}, no matching skill in this repo)"
        fi
    done

    [[ "${mode}" == "sync" ]] || return 0

    echo ""
    local to_sync=("${missing[@]}" "${stale[@]}")
    if [[ "${#to_sync[@]}" -eq 0 ]]; then
        echo "skill-audit: nothing to sync"
        return 0
    fi

    local confirm
    for name in "${to_sync[@]}"; do
        global_dest="${global_skills_dir}/${name}"
        if [[ "${auto_yes}" -eq 0 ]]; then
            read -rp "Sync ${name} -> ${global_dest}? [y/N] " confirm
            [[ "${confirm}" =~ ^[Yy]$ ]] || continue
        fi
        mkdir -p "${global_skills_dir}"
        rm -rf "${global_dest}"
        cp -r "${skills_dir}/${name}" "${global_dest}"
        echo "Synced ${name} -> ${global_dest}"
    done
}
