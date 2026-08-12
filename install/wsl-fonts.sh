#!/usr/bin/env bash
## @make 42 Environment-Specific | Install Starship + JetBrainsMono Nerd Font (WSL to Windows)
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

##
## The terminal font setting is NOT patched in here. It is tracked, in
## .vscode/.symlinked-user-settings.json, and `make vscode` symlinks Windows'
## settings.json at that file.
##
## This block used to rewrite settings.json in place, and every run printed
## ">>> VSCode settings not found at expected path. Manually add ...". Both
## halves were wrong. The `[[ -f ]]` test always failed because `make vscode`
## makes settings.json a Windows-side symlink to a UNC \\wsl.localhost\... path,
## which WSL cannot dereference (`ls` reports an I/O error on it) -- so the
## advice was to hand-add a key that was already set. And had the test ever
## passed, it would have clobbered the tracked value
## ("JetBrainsMono Nerd Font Mono, JetBrainsMono NFM, monospace") with a
## strictly worse one, in a file that is a symlink into this repo.
##

echo "VSCode terminal font is tracked in .vscode/.symlinked-user-settings.json (run: make vscode)"
