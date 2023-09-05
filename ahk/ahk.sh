#!/usr/bin/env bash


# Get autohotkey file from this repo in WSL2, start in Windows environment
# May need to Powershell Admin run: `Set-ExecutionPolicy RemoteSigned`


script=$(readlink -f "$BASH_SOURCE")
script_path=$(dirname "$script")
ahk_file_path=$script_path/dev_shortcuts.ahk
ahk_secrets_path=$script_path/secrets.ahk
touch $ahk_secrets_path

# use "open" CLI arg to open the file for edits
if [ "$1" = "open" ]; then
    code $ahk_file_path
elif [ "$1" = "open_secrets" ]; then
    code $ahk_secrets_path
elif [ "$1" = "kill" ]; then
    ahk_pids=$(powershell.exe "Get-Process AutoHotkey | Select-Object -ExpandProperty Id")
    for pid in $ahk_pids; do
        powershell.exe "Stop-Process -Id $pid '-Force'"
    done
else
    win_drive_path=$(wslpath -w -a "$ahk_file_path")
    powershell.exe -Command "Start-Process '${win_drive_path}'" 2> /dev/null
    win_drive_path=$(wslpath -w -a "$ahk_secrets_path")
    powershell.exe -Command "Start-Process '${win_drive_path}'" 2> /dev/null
fi
