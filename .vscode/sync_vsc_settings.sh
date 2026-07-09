#!/usr/bin/env bash

set -euo pipefail

source ~/.bashrc

script_dir=$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")
settings_source="${script_dir}/.symlinked-user-settings.json"

if [[ -z "${WINDOWS_USERNAME:-}" ]]; then
    echo "Error: WINDOWS_USERNAME not set in environment" >&2
    exit 1
fi

windows_target="/mnt/c/Users/${WINDOWS_USERNAME}/AppData/Roaming/Code/User/settings.json"
wsl_source_path=$(wslpath -w "${settings_source}")

if [[ -L "${windows_target}" ]]; then
    echo "Symlink already exists at ${windows_target}"
    exit 0
fi

if [[ -f "${windows_target}" ]]; then
    echo "Backing up existing settings to settings.json.bak"
    cp "${windows_target}" "${windows_target}.bak"
    rm "${windows_target}"
fi

windows_target_win=$(wslpath -w "${windows_target}")

powershell.exe -Command "Start-Process powershell -Verb RunAs -Wait -ArgumentList \"-Command New-Item -ItemType SymbolicLink -Path '${windows_target_win}' -Target '${wsl_source_path}'\"" || {
    echo "ERROR: Symlink creation failed. Enable Developer Mode to avoid the UAC prompt:" >&2
    echo "  Windows Settings > For developers > Developer Mode > On" >&2
    exit 1
}

echo "VS Code settings symlinked to dotfiles"

# Symlink keybindings
keybindings_source="${script_dir}/keybindings.json"
keybindings_target="/mnt/c/Users/${WINDOWS_USERNAME}/AppData/Roaming/Code/User/keybindings.json"
keybindings_target_win=$(wslpath -w "${keybindings_target}")
keybindings_wsl_source=$(wslpath -w "${keybindings_source}")

if [[ -L "${keybindings_target}" ]]; then
    echo "Keybindings symlink already exists"
else
    [[ -f "${keybindings_target}" ]] && cp "${keybindings_target}" "${keybindings_target}.bak" && rm "${keybindings_target}"
    powershell.exe -Command "Start-Process powershell -Verb RunAs -Wait -ArgumentList \"-Command New-Item -ItemType SymbolicLink -Path '${keybindings_target_win}' -Target '${keybindings_wsl_source}'\"" || {
        echo "ERROR: Keybindings symlink creation failed." >&2
        exit 1
    }
    echo "VS Code keybindings symlinked to dotfiles"
fi
