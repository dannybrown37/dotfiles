#!/usr/bin/env bash

## Screen recording mover

clip() {  # @doc Copy a screen recording to OneDrive with fzf selection: clip [--reset]
    local config_dir="${HOME}/.config/screen-recording-mover"
    local config_file="${config_dir}/config"
    local onedrive_config="${config_dir}/onedrive-root"

    if [[ -z "${CLIP_DEST:-}" ]]; then
        echo "CLIP_DEST is not set (Windows path to destination folder)" >&2
        echo "e.g. export CLIP_DEST='C:\\Users\\me\\whelen.com\\Recordings'" >&2
        return 1
    fi

    if [[ "${1:-}" == "--help" ]]; then
        echo "Usage: clip [--reset]"
        echo "Select a screen recording via fzf, optionally rename, copy to CLIP_DEST."
        echo "Set CLIP_SHAREPOINT_BASE_URL to auto-open the SharePoint link after copy."
        return 0
    fi

    if [[ "${1:-}" == "--reset" ]]; then
        rm -f "${config_file}" "${onedrive_config}"
        echo "Config cleared."
        return 0
    fi

    local win_user
    win_user="$(/mnt/c/Windows/System32/cmd.exe /c "echo %USERNAME%" 2>/dev/null | tr -d '\r')"
    local win_home="C:\\Users\\${win_user}"
    local recordings_dir="${win_home}\\Videos\\Screen Recordings"

    local recording
    recording="$(powershell.exe -NoProfile -Command \
        "Get-ChildItem '${recordings_dir}' -File | Sort-Object LastWriteTime -Descending | Select-Object -ExpandProperty Name" \
        2>/dev/null | tr -d '\r' \
        | fzf --prompt="Screen recording: " --height=40%)" || { return 0; }

    local extension="${recording##*.}"
    local basename="${recording%.*}"
    local new_name
    read -r -p "Rename? [${basename}]: " new_name
    local final_name="${new_name:+${new_name}.${extension}}"
    final_name="${final_name:-${recording}}"

    local src="${recordings_dir}\\${recording}"
    local dst="${CLIP_DEST}\\${final_name}"

    if powershell.exe -NoProfile -Command "Test-Path '${dst}'" 2>/dev/null | grep -qi true; then
        local confirm
        read -r -p "File already exists. Overwrite? [y/N]: " confirm
        if [[ "${confirm}" != [yY] ]]; then
            echo "Aborted."
            return 0
        fi
    fi

    powershell.exe -NoProfile -Command "Copy-Item '${src}' '${dst}' -Force" 2>/dev/null
    echo "Copied: ${final_name} -> ${CLIP_DEST##*\\}"

    if [[ -n "${CLIP_SHAREPOINT_BASE_URL:-}" ]]; then
        local encoded_name
        encoded_name="$(powershell.exe -NoProfile -Command \
            "[uri]::EscapeDataString('${final_name}')" 2>/dev/null | tr -d '\r')"
        local remote_url="${CLIP_SHAREPOINT_BASE_URL}/${encoded_name}"
        echo -n "${remote_url}" | clip.exe
        echo "URL copied to clipboard."
    fi
}
