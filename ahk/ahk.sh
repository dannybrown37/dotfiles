#!/usr/bin/env bash

# Get autohotkey files from this repo in WSL2, start in Windows environment
# May need to Powershell Admin run: `Set-ExecutionPolicy RemoteSigned`

if [[ -z "${ON_WINDOWS}" ]]; then
    echo "AHK is only available from WSL or Git Bash"
    exit 1
fi

if [[ -z "${DOTFILES_DIR}" ]]; then
    echo "Something went wrong with your .bashrc, no value for DOTFILES_DIR"
    exit 1
fi

hotstrings_path="${DOTFILES_DIR}/ahk/hotstrings.ahk"
ahk_secrets_path="${DOTFILES_DIR}/ahk/secrets.ahk"
all_ahk_files=("${DOTFILES_DIR}/ahk/"*.ahk)

if [[ ! -e "${ahk_secrets_path}" ]]; then
    echo "#SingleInstance Force" >>"${ahk_secrets_path}"
fi

hotstring_definitions=$(grep -oE '::[^:]+::[^:]+' "$hotstrings_path")

if [[ "$1" = "help" ]]; then
    echo "$hotstring_definitions" | fzf --sort
elif [[ "$1" = "open" ]]; then
    nvim "${hotstrings_path}" || code "{$hotstrings_path}"
elif [[ "$1" = "secrets" ]]; then
    nvim "${ahk_secrets_path}" || code "${ahk_secrets_path}"
elif [[ "$1" = "kill" ]]; then
    ahk_pids=$(
        powershell.exe -File ./run_as_admin.ps1 \
            "Get-Process AutoHotkey* | Select-Object -ExpandProperty Id"
    )
    for pid in ${ahk_pids}; do
        echo "Starting ${pid}"
        if [[ -n "${WSL_DISTRO_NAME}" ]]; then # handle WSL
            powershell.exe -File ./run_as_admin.ps1 "Stop-Process -Id ${pid} '-Force'"
        else # handle Git Bash
            powershell.exe -File ./run_as_admin.ps1 "Stop-Process -Id ${pid} -Force"
        fi
    done
else
    for ahk_file in "${all_ahk_files[@]}"; do
        if [[ -n "${WSL_DISTRO_NAME}" ]]; then # handle WSL
            win_drive_path=$(wslpath -w -a "${ahk_file}")
        else # handle Git Bash
            win_drive_path=$(cygpath -w -a "${ahk_file}")
        fi
        powershell.exe -File ./run_as_admin.ps1 \
            -Command "Start-Process '${win_drive_path}'" 2>/dev/null
    done
fi
