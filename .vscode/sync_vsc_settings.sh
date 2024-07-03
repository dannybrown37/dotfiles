#!/usr/bin/env bash

source ~/.bashrc

vscode_setup_script_path=$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")
synced_settings_path="${vscode_setup_script_path}/synced-settings.json"

# Path to settings.json in WSL
if [[ -z "${WINDOWS_USERNAME}" ]]; then
  echo "Error: no Windows username found in environment"
  exit 1
fi
windows_settings_path="/mnt/c/Users/${WINDOWS_USERNAME}/AppData/Roaming/Code/User/settings.json"

echo "Installing from ${windows_settings_path}"

# Check if settings.json file already exists -- if so, read it
if [[ -f "${windows_settings_path}" ]]; then
  # Print contents of settings file
  echo "CurrentVSCode settings:"
  cat "${windows_settings_path}"
else
  echo "{}" > "${windows_settings_path}"
  echo "There is not an existing VSCode settings path in Windows"
fi

# merge existing and default settings
merged_settings=$(
  jq -s '.[0] * .[1]' "${windows_settings_path}" "${synced_settings_path}" |
  jq 'to_entries | sort_by(.key) | from_entries'
)


echo "${merged_settings}" | jq '.' > "${windows_settings_path}"
echo "${merged_settings}" | jq '.' > "${synced_settings_path}"

echo "New VSCode settings:"
cat "${windows_settings_path}"

echo "VSCode settings synced between Windows and WSL"
