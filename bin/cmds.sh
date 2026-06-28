# @doc Search all commands, aliases, and AHK hotkeys via fzf
cmds() {
    local dotfiles_dir="${DOTFILES_DIR:-$HOME/projects/dotfiles}"
    local entries=""
    local -A documented_aliases

    _cmds_strip_quotes() { sed "s/^['\"]//;s/['\"]$//" <<< "$1"; }

    local file source_label
    for file in "${dotfiles_dir}/config/.bash_aliases" "${dotfiles_dir}/config/.bashrc"; do
        [[ -f "$file" ]] || continue
        source_label="${file#"${dotfiles_dir}"/}"
        while IFS= read -r line; do
            if [[ "$line" =~ ^[[:space:]]*alias[[:space:]]+([a-zA-Z0-9_-]+)=.*#[[:space:]]*@doc[[:space:]]+(.*) ]]; then
                local name="${BASH_REMATCH[1]}"
                entries+=$'[alias]\t'"${name}"$'\t'"${source_label}"$'\t'"${BASH_REMATCH[2]}"$'\n'
                documented_aliases["$name"]=1
            elif [[ "$line" =~ ^[[:space:]]*alias[[:space:]]+([a-zA-Z0-9_-]+)=(.*)[[:space:]]*$ ]]; then
                local name="${BASH_REMATCH[1]}"
                if [[ -z "${documented_aliases[$name]:-}" ]]; then
                    local val
                    val=$(_cmds_strip_quotes "${BASH_REMATCH[2]}")
                    entries+=$'[alias]\t'"${name}"$'\t'"${source_label}"$'\t'"${val}"$'\n'
                    documented_aliases["$name"]=1
                fi
            elif [[ "$line" =~ ^[[:space:]]*(function[[:space:]]+)?([a-zA-Z0-9_-]+)\(\).*#[[:space:]]*@doc[[:space:]]+(.*) ]]; then
                entries+=$'[func]\t'"${BASH_REMATCH[2]}"$'\t'"${source_label}"$'\t'"${BASH_REMATCH[3]}"$'\n'
            fi
        done < "$file"
    done

    local dir
    for dir in "${dotfiles_dir}/bin" "${dotfiles_dir}/scripts"; do
        [[ -d "$dir" ]] || continue
        for file in "$dir"/*; do
            [[ -f "$file" ]] || continue
            local name
            name=$(basename "$file" .sh)
            source_label="${file#"${dotfiles_dir}"/}"
            while IFS= read -r line; do
                if [[ "$line" =~ ^#[[:space:]]*@doc[[:space:]]+(.*) ]]; then
                    entries+=$'[cmd]\t'"${name}"$'\t'"${source_label}"$'\t'"${BASH_REMATCH[1]}"$'\n'
                fi
            done < "$file"
        done
    done

    for file in "${dotfiles_dir}/ahk"/*.ahk; do
        [[ -f "$file" ]] || continue
        source_label="${file#"${dotfiles_dir}"/}"
        while IFS= read -r line; do
            if [[ "$line" =~ ^";"[[:space:]]*"@doc"[[:space:]]+(.*) ]]; then
                entries+=$'[ahk]\t'"${BASH_REMATCH[1]%%:*}"$'\t'"${source_label}"$'\t'"${BASH_REMATCH[1]#*: }"$'\n'
            fi
        done < "$file"
    done

    while IFS= read -r line; do
        if [[ "$line" =~ ^alias[[:space:]]+([a-zA-Z0-9_-]+)=(.*) ]]; then
            local name="${BASH_REMATCH[1]}"
            if [[ -z "${documented_aliases[$name]:-}" ]]; then
                local val
                val=$(_cmds_strip_quotes "${BASH_REMATCH[2]}")
                entries+=$'[alias]\t'"${name}"$'\t'"shell"$'\t'"${val}"$'\n'
            fi
        fi
    done < <(alias 2>/dev/null)

    local selected
    selected=$(printf '%s' "$entries" | sed '/^$/d' | sort -t$'\t' -k2 | column -t -s$'\t' | fzf --prompt="cmds> " --height=40% --reverse) || return 0

    echo "$selected"
    printf '%s' "$selected" | xclip -selection clipboard
}
