#!/usr/bin/env bash

script=$(readlink -f "$BASH_SOURCE")
script_path=$(dirname "$script")
default_settings_path=$script_path/default_settings.json

# Path to settings.json in WSL
vscode_settings_path="/mnt/c/Users/${WINDOWS_USERNAME}/AppData/Roaming/Code/User/settings.json"

echo $vscode_settings_path

# Check if settings.json file already exists -- if so, read it
if [ -f "$vscode_settings_path" ]; then
  # Print contents of settings file
  echo "CurrentVSCode settings:"
  cat "$vscode_settings_path"
else
  echo "{}" > "$vscode_settings_path"
  echo "Created an empty settings.json"
fi

merged_settings=$(jq -s '.[0] * .[1]' "$vscode_settings_path" "$default_settings_path")

echo $merged_settings | jq '.' > "$vscode_settings_path"

echo "New VSCode settings:"
cat $vscode_settings_path
