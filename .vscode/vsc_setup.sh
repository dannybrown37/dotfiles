#!/usr/bin/env bash

source ~/.bashrc

vscode_setup_script_path=$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")
default_settings_path="${vscode_setup_script_path}/settings.json"
default_extensions_path="${vscode_setup_script_path}/extensions.txt"

# Path to settings.json in WSL
if [[ -z "${WINDOWS_USERNAME}" ]]; then
  echo "Error: no Windows username found in environment"
  exit 1
fi
vscode_settings_path="/mnt/c/Users/${WINDOWS_USERNAME}/AppData/Roaming/Code/User/settings.json"

echo "Installing from ${vscode_settings_path}"

# Check if settings.json file already exists -- if so, read it
if [[ -f "${vscode_settings_path}" ]]; then
  # Print contents of settings file
  echo "CurrentVSCode settings:"
  cat "${vscode_settings_path}"
else
  echo "{}" > "${vscode_settings_path}"
  echo "There is not an existing VSCode settings path in Windows"
fi

# merge existing and default settings
merged_settings=$(jq -s '.[0] * .[1]' "${vscode_settings_path}" "${default_settings_path}")

echo "${merged_settings}" | jq '.' > "${vscode_settings_path}"

echo "New VSCode settings:"
cat "${vscode_settings_path}"

# Now handle extensions
installed_extensions=$(code --list-extensions)
extensions_to_install=()

while IFS= read -r extension_id; do
  if [[ -z "${extension_id}" || "${extension_id}" =~ ^# ]]; then
    continue
  fi
  if [[ ! "${installed_extensions}" == *"${extension_id}"* ]]; then
    extensions_to_install+=("${extension_id}")
  fi
done < "${default_extensions_path}"

for extension_id in "${extensions_to_install[@]}"; do
  echo "Installing extension: ${extension_id}"
  code --install-extension "${extension_id}"
done

echo "All extensions have been installed."
