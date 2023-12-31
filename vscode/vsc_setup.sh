#!/usr/bin/env bash

source ~/.bashrc

vscode_setup_script_path=$(dirname $(readlink -f "$BASH_SOURCE"))
default_settings_path=$vscode_setup_script_path/.default_settings.json
default_extensions_path=$vscode_setup_script_path/.extensions

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
extensions_to_install=()

while IFS= read -r extension_id; do
  if [[ ! "$installed_extensions" == *"$extension_id"* ]]; then
    extensions_to_install+=("$extension_id")
  fi
done < "$default_extensions_path"

for extension_id in "${extensions_to_install[@]}"; do
  echo "Installing extension: $extension_id"
  code --install-extension "$extension_id"
done

echo "All extensions have been installed."
