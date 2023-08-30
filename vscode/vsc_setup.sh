#!/usr/bin/env bash

source ~/.bashrc

if [ -z "$WINDOWS_USERNAME" ]; then
  ls /mnt/c/Users
  read -p "What is your Windows username? " windows_username
  echo "export WINDOWS_USERNAME=$windows_username" >> ~/.bashrc
  source ~/.bashrc
fi

script=$(readlink -f "$BASH_SOURCE")
script_path=$(dirname "$script")
default_settings_path=$script_path/default_settings.json
default_extensions_path=$script_path/default_extensions.txt

# Path to settings.json in WSL
vscode_settings_path="/mnt/c/Users/$WINDOWS_USERNAME/AppData/Roaming/Code/User/settings.json"

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

# merge existing and default settings
merged_settings=$(jq -s '.[0] * .[1]' "$vscode_settings_path" "$default_settings_path")

echo $merged_settings | jq '.' > "$vscode_settings_path"

echo "New VSCode settings:"
cat $vscode_settings_path


# Now handle extensions
installed_extensions=$(code --list-extensions)
not_installed=()

while IFS= read -r extension_id; do
  if [[ ! "$installed_extensions" == *"$extension_id"* ]]; then
    echo "Installing extension: $extension_id"
    code --install-extension "$extension_id"
  else
    not_installed+=("$extension_id")
  fi
done < "$default_extensions_path"

echo "VSCode extensions already installed: ${not_installed[@]}"
