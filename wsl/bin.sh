#!/usr/bin/env bash

##
## Assorted Functions for Windodws Subsystem for Linux
##


function open_vs_code_settings_folder_in_windows_environment() {
    if [[ -z "${ON_WINDOWS}" ]]; then
        echo "You're not on Windows"
        return
    fi
    windows_path=$(wslpath -w "/mnt/c/Users/${WINDOWS_USERNAME}/AppData/Roaming/Code/User/")
    explorer.exe "$windows_path"
}

