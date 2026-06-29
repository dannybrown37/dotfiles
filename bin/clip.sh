#!/usr/bin/env bash

## Screen recording mover

clip() {  # @doc Copy a screen recording to OneDrive with fzf selection: clip [--reset]
    local config_dir="${HOME}/.config/screen-recording-mover"
    local config_file="${config_dir}/config"
    local onedrive_config="${config_dir}/onedrive-root"
    local win_user win_home recordings_dir

    win_user="$(/mnt/c/Windows/System32/cmd.exe /c "echo %USERNAME%" 2>/dev/null | tr -d '\r')"
    win_home="/mnt/c/Users/${win_user}"
    recordings_dir="${win_home}/Videos/Screen Recordings"

    if [[ "${1:-}" == "--help" ]]; then
        echo "Usage: clip [--reset]"
        echo "Select a screen recording via fzf, optionally rename, copy to OneDrive."
        return 0
    fi

    if [[ "${1:-}" == "--reset" ]]; then
        rm -f "${config_file}" "${onedrive_config}"
        echo "Config cleared."
        return 0
    fi

    if [[ ! -d "${recordings_dir}" ]]; then
        echo "Screen Recordings folder not found: ${recordings_dir}" >&2
        return 1
    fi

    local recording
    recording="$(find "${recordings_dir}" -maxdepth 1 -type f -printf '%T@ %f\n' \
        | sort -rn \
        | cut -d' ' -f2- \
        | fzf --prompt="Screen recording: " --height=40%)" || { return 0; }

    local extension="${recording##*.}"
    local basename="${recording%.*}"
    local new_name
    read -r -p "Rename? [${basename}]: " new_name
    local final_name="${new_name:+${new_name}.${extension}}"
    final_name="${final_name:-${recording}}"

    local onedrive_root
    if [[ -f "${onedrive_config}" ]] && [[ -d "$(cat "${onedrive_config}")" ]]; then
        onedrive_root="$(cat "${onedrive_config}")"
    else
        onedrive_root="$(find "${win_home}" -maxdepth 1 -type d -name "OneDrive*" 2>/dev/null \
            | fzf --prompt="OneDrive root: " --height=40%)" || { return 0; }
        mkdir -p "${config_dir}"
        echo "${onedrive_root}" > "${onedrive_config}"
    fi

    local destination
    if [[ -f "${config_file}" ]] && [[ -d "$(cat "${config_file}")" ]]; then
        destination="$(cat "${config_file}")"
    else
        local selected
        selected="$(find "${onedrive_root}" -maxdepth 1 -type d 2>/dev/null \
            | sed "s|${onedrive_root}/||" \
            | sed '/^$/d' \
            | fzf --prompt="OneDrive destination: " --height=40%)" || { return 0; }
        destination="${onedrive_root}/${selected}"
        mkdir -p "${config_dir}"
        echo "${destination}" > "${config_file}"
    fi

    local src="${recordings_dir}/${recording}"
    local dst="${destination}/${final_name}"

    if [[ -f "${dst}" ]]; then
        local confirm
        read -r -p "File already exists. Overwrite? [y/N]: " confirm
        if [[ "${confirm}" != [yY] ]]; then
            echo "Aborted."
            return 0
        fi
    fi

    cp "${src}" "${dst}"
    echo "Copied: ${final_name} -> ${destination##*/}/"
}
