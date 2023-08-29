#!/usr/bin/env bash
# Get autohotkey file from this repo in WSL2, start in Windows environment
# May need to Powershell Admin run: `Set-ExecutionPolicy RemoteSigned`

script=$(readlink -f "$BASH_SOURCE")
script_path=$(dirname "$script")
ahk_file_path=$script_path/dev_shortcuts.ahk

# use "open" CLI arg to open the file for edits
if [ "$1" = "open" ]; then
    code $ahk_file_path
else
    win_drive_path=$(wslpath -w -a "$ahk_file_path")
    powershell.exe /c start "${win_drive_path}"
fi
