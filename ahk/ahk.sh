#!/usr/bin/env bash


# Get autohotkey files from this repo in WSL2, start in Windows environment
# May need to Powershell Admin run: `Set-ExecutionPolicy RemoteSigned`


if [[ -z "$WSL_DISTRO_NAME" || "$MSYSTEM" = "MINGW64" ]]; then
    echo "AHK is only available from WSL or Git Bash"
    exit 1
fi


SCRIPT=$(readlink -f "${BASH_SOURCE[0]}")
SCRIPT_PATH=$(dirname "$SCRIPT")
AHK_FILE_PATH=$SCRIPT_PATH/dev_shortcuts.ahk
AHK_SECRETS_PATH=$SCRIPT_PATH/secrets.ahk
touch "${AHK_SECRETS_PATH}"

# use "open" CLI arg to open the file for edits
if [[ "$1" = "open" ]]; then
    code "${AHK_FILE_PATH}"
elif [[ "$1" = "open_secrets" ]]; then
    code "${AHK_SECRETS_PATH}"
elif [[ "$1" = "kill" ]]; then
    AHK_PIDS=$(powershell.exe "Get-Process AutoHotkey | Select-Object -ExpandProperty Id")
    for PID in $AHK_PIDS; do
        if [ -n "$WSL_DISTRO_NAME" ]; then  # handle WSL
            powershell.exe "Stop-Process -Id $PID '-Force'"
        else  # handle Git Bash
            powershell.exe "Stop-Process -Id $PID -Force"
        fi
    done
else
    if [[ -n "$WSL_DISTRO_NAME" ]]; then  # handle WSL
        WIN_DRIVE_PATH=$(wslpath -w -a "${AHK_FILE_PATH}")
        WIN_DRIVE_PATH_2=$(wslpath -w -a "${AHK_SECRETS_PATH}")
    else  # handle Git Bash
        WIN_DRIVE_PATH=$(cygpath -w -a "${AHK_FILE_PATH}")
        WIN_DRIVE_PATH_2=$(cygpath -w -a "${AHK_SECRETS_PATH}")
    fi
    powershell.exe -Command "Start-Process '${WIN_DRIVE_PATH}'" 2> /dev/null
    powershell.exe -Command "Start-Process '${WIN_DRIVE_PATH_2}'" 2> /dev/null
fi
