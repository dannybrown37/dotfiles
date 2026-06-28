
cmds() { # @doc Search all commands, aliases, and AHK hotkeys via fzf
    local dotfiles_dir="${DOTFILES_DIR:-$HOME/projects/dotfiles}"
    local entries=""

    # Parse @doc from .bash_aliases and .bashrc
    local file
    for file in "${dotfiles_dir}/config/.bash_aliases" "${dotfiles_dir}/config/.bashrc"; do
        [[ -f "$file" ]] || continue
        while IFS= read -r line; do
            if [[ "$line" =~ ^[[:space:]]*alias[[:space:]]+([a-zA-Z0-9_-]+)=.*#[[:space:]]*@doc[[:space:]]+(.*) ]]; then
                entries+="[alias]  ${BASH_REMATCH[1]}  ${BASH_REMATCH[2]}"$'\n'
            elif [[ "$line" =~ ^[[:space:]]*(function[[:space:]]+)?([a-zA-Z0-9_-]+)\(\).*#[[:space:]]*@doc[[:space:]]+(.*) ]]; then
                entries+="[func]   ${BASH_REMATCH[2]}  ${BASH_REMATCH[3]}"$'\n'
            fi
        done < "$file"
    done

    # Parse @doc from bin/ and scripts/
    local dir
    for dir in "${dotfiles_dir}/bin" "${dotfiles_dir}/scripts"; do
        [[ -d "$dir" ]] || continue
        for file in "$dir"/*; do
            [[ -f "$file" ]] || continue
            local name
            name=$(basename "$file" .sh)
            while IFS= read -r line; do
                if [[ "$line" =~ ^#[[:space:]]*@doc[[:space:]]+(.*) ]]; then
                    entries+="[cmd]    ${name}  ${BASH_REMATCH[1]}"$'\n'
                fi
            done < "$file"
        done
    done

    # Parse @doc from ahk/
    for file in "${dotfiles_dir}/ahk"/*.ahk; do
        [[ -f "$file" ]] || continue
        while IFS= read -r line; do
            if [[ "$line" =~ ^";"[[:space:]]*"@doc"[[:space:]]+(.*) ]]; then
                entries+="[ahk]    ${BASH_REMATCH[1]}"$'\n'
            fi
        done < "$file"
    done

    local selected
    selected=$(printf '%s' "$entries" | sed '/^$/d' | sort -t']' -k2 | fzf --prompt="cmds> " --height=40% --reverse) || return 0

    echo "$selected"
    printf '%s' "$selected" | xclip -selection clipboard
}
