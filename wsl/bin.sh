#!/usr/bin/env bash

##
## Assorted Functions for Windodws Subsystem for Linux
##


function open_vs_code_settings_folder_in_windows_environment {
    if [[ -z "${ON_WINDOWS}" ]]; then
        echo "You're not on Windows"
        return
    fi
    windows_path=$(wslpath -w "/mnt/c/Users/${WINDOWS_USERNAME}/AppData/Roaming/Code/User/")
    explorer.exe "$windows_path"
}
alias vscw='open_vs_code_settings_folder_in_windows_environment'


function copy_from_windows_downloads_folder_to_wsl {
    if [[ -z "${ON_WINDOWS}" ]]; then
        echo "You're not on Windows"
        return
    fi
    local downloads_path="/mnt/c/Users/${WINDOWS_USERNAME}/Downloads"
    local selected_file=$(find "$downloads_path" -maxdepth 1 -type f -printf "%f\n" | fzf --preview "file {}" --preview-window "right:50%:wrap" --select-1)
    local wsl_downloads_path="${HOME}/downloads"
    mkdir -p "$wsl_downloads_path"
    cp "$downloads_path/$selected_file" "$wsl_downloads_path/$selected_file"
    echo "Copied $selected_file to $wsl_downloads_path"
}
alias cfw='copy_from_windows_downloads_folder_to_wsl'
