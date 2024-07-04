#!/usr/bin/bash


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

HOTSTRINGS_PATH="${DOTFILES_DIR}/ahk/hotstrings.ahk"
AHK_SECRETS_PATH="${DOTFILES_DIR}/ahk/secrets.ahk"
ALL_AHK_FILES=("${DOTFILES_DIR}/ahk/"*.ahk)

if [[ ! -e "${AHK_SECRETS_PATH}" ]]; then
    echo "#SingleInstance Force" >> "${AHK_SECRETS_PATH}"
fi

HOTSTRING_DEFINITIONS=$(grep -oE '::[^:]+::[^:]+' "$HOTSTRINGS_PATH")

if [[ "$1" = "help" ]]; then
    echo "$HOTSTRING_DEFINITIONS" | fzf --sort
elif [[ "$1" = "open" ]]; then
    code "${HOTSTRINGS_PATH}"
elif [[ "$1" = "open_secrets" ]]; then
    code "${AHK_SECRETS_PATH}"
elif [[ "$1" = "kill" ]]; then
    AHK_PIDS=$(powershell.exe "Get-Process AutoHotkey* | Select-Object -ExpandProperty Id")
    for PID in ${AHK_PIDS}; do
        if [[ -n "${WSL_DISTRO_NAME}" ]]; then  # handle WSL
            powershell.exe "Stop-Process -Id ${PID} '-Force'"
        else  # handle Git Bash
            powershell.exe "Stop-Process -Id ${PID} -Force"
        fi
    done
else
    for AHK_FILE in "${ALL_AHK_FILES[@]}"; do
        if [[ -n "${WSL_DISTRO_NAME}" ]]; then  # handle WSL
            WIN_DRIVE_PATH=$(wslpath -w -a "${AHK_FILE}")
        else  # handle Git Bash
            WIN_DRIVE_PATH=$(cygpath -w -a "${AHK_FILE}")
        fi
        powershell.exe -Command "Start-Process '${WIN_DRIVE_PATH}'" 2> /dev/null
    done
fi
