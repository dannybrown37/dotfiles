#!/usr/bin/env bash
# shellcheck disable=SC1090,SC1091

set -euo pipefail

# Install Starship prompt (https://starship.rs)
if ! command -v starship &>/dev/null; then
    curl -sS https://starship.rs/install.sh | sh -s -- --yes
else
    echo "Starship already installed, skipping..."
fi

# Install JetBrainsMono Nerd Font on Windows (required for Starship to render icons).
# WSL terminals are rendered by Windows, so fonts must be installed on the Windows side.
# shellcheck disable=SC2016
# Single quotes intentional: $env:UserName is PowerShell syntax, not bash
readonly windows_username=$(powershell.exe '$env:UserName' 2>/dev/null | tr -d '\r\n')
readonly user_fonts_path="/mnt/c/Users/${windows_username}/AppData/Local/Microsoft/Windows/Fonts"

if [[ -z "$(find "${user_fonts_path}" -maxdepth 1 -iname 'JetBrainsMono*' 2>/dev/null | head -1)" ]]; then
    echo "Installing JetBrainsMono Nerd Font to Windows (~200MB download, one-time)..."
    font_tmp=$(mktemp -d)
    trap 'rm -rf "${font_tmp}"' EXIT

    cat > "${font_tmp}/install_font.ps1" << 'PWSH'
$ProgressPreference = 'SilentlyContinue'
$FontZip = "$env:TEMP\JetBrainsMono.zip"
$FontDir = "$env:TEMP\JetBrainsMono_nf"
$UserFontDir = "$env:LOCALAPPDATA\Microsoft\Windows\Fonts"

Write-Host "Downloading JetBrainsMono Nerd Font..."
Invoke-WebRequest -Uri "https://github.com/ryanoasis/nerd-fonts/releases/latest/download/JetBrainsMono.zip" -OutFile $FontZip -UseBasicParsing
Write-Host "Extracting..."
Expand-Archive -Path $FontZip -DestinationPath $FontDir -Force
New-Item -ItemType Directory -Force -Path $UserFontDir | Out-Null
Write-Host "Installing to user font directory..."
Get-ChildItem -Path $FontDir -Filter "*.ttf" -Recurse | ForEach-Object {
    Copy-Item $_.FullName (Join-Path $UserFontDir $_.Name) -Force
    New-ItemProperty -Path "HKCU:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts" `
        -Name ($_.BaseName + " (TrueType)") -Value $_.Name -PropertyType String -Force | Out-Null
}
Remove-Item $FontZip -Force -ErrorAction SilentlyContinue
Remove-Item $FontDir -Recurse -Force -ErrorAction SilentlyContinue
Write-Host "JetBrainsMono Nerd Font installed successfully."
PWSH

    font_tmp_win=$(wslpath -w "${font_tmp}")
    powershell.exe -ExecutionPolicy Bypass -File "${font_tmp_win}\\install_font.ps1"

else
    echo "JetBrainsMono Nerd Font already installed, skipping..."
fi

# Configure VSCode terminal font (works whether font was just installed or already present).
readonly vscode_settings="/mnt/c/Users/${windows_username}/AppData/Roaming/Code/User/settings.json"

if [[ -f "${vscode_settings}" ]]; then
    python3 - "${vscode_settings}" << 'PYEOF'
import re, json, sys

path = sys.argv[1]
text = open(path).read()
text = re.sub(r'//[^\n]*', '', text)
text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
text = re.sub(r',(\s*[}\]])', r'\1', text)
data = json.loads(text)
data['terminal.integrated.fontFamily'] = 'JetBrainsMono Nerd Font'
with open(path, 'w') as f:
    json.dump(data, f, indent=4)
    f.write('\n')
PYEOF
    echo "VSCode terminal font set to 'JetBrainsMono Nerd Font' in settings.json"
else
    echo ""
    echo ">>> VSCode settings not found at expected path. Manually add to settings.json:"
    echo '    "terminal.integrated.fontFamily": "JetBrainsMono Nerd Font"'
fi
