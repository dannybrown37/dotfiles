#!/usr/bin/env bash

# Path to settings.json in WSL
vscode_settings_path="/mnt/c/Users/${WINDOWS_USERNAME}/AppData/Roaming/Code/User/settings.json"

echo $vscode_settings_path

# Check if file exists
if [ -f "$vscode_settings_path" ]; then

  # Print contents of settings file
  echo "VSCode settings:"
  cat "$vscode_settings_path"

else
  echo "Settings file not found at ${vscode_settings_path}"
fi
