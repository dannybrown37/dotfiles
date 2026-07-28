#!/usr/bin/env bash
# shellcheck disable=SC1090,SC1091

set -euo pipefail

# Install Starship prompt (https://starship.rs)
if ! command -v starship &>/dev/null; then
    curl -sS https://starship.rs/install.sh | sh -s -- --yes
else
    echo "Starship already installed, skipping..."
fi

# WSL terminals are rendered by Windows, so Nerd Fonts must be installed Windows-side.
# Terminals resolve the typographic family name (name table id 16), while Windows'
# font enumeration reports the shorter GDI family name (id 1) -- hence both constants.
# The "Mono" build is the one with uniform advance widths, which is what a terminal needs;
# the plain "JetBrainsMono Nerd Font" build is proportional and renders ragged columns.
readonly font_family="JetBrainsMono Nerd Font Mono"
readonly gdi_family="JetBrainsMono NFM"
readonly font_stack="${font_family}, ${gdi_family}, monospace"

# shellcheck disable=SC2016
# Single quotes intentional: $env:UserName is PowerShell syntax, not bash
readonly windows_username=$(powershell.exe '$env:UserName' 2>/dev/null | tr -d '\r\n')

# sync_vsc_settings.sh symlinks VSCode's settings.json to this repo file via a UNC path
# back into WSL. WSL cannot traverse that Windows -> UNC -> WSL hop (it fails with EIO),
# so the Windows-side path is unreadable from here and the repo file is the one to edit.
repo_root=$(dirname "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")")
readonly repo_root
readonly vscode_settings="${repo_root}/.vscode/.symlinked-user-settings.json"

# Presence on disk proves nothing: a font is only usable once Windows has loaded it into
# the session font table. Fonts registered mid-session stay invisible to every app until
# something calls AddFontResourceW or the machine reboots, so enumeration is the only
# honest check.
font_is_available() {
    local found
    found=$(powershell.exe -NoProfile -Command "
        Add-Type -AssemblyName System.Drawing
        \$c = New-Object System.Drawing.Text.InstalledFontCollection
        if (\$c.Families | Where-Object { \$_.Name -eq '${gdi_family}' }) { 'yes' }
    " 2>/dev/null | tr -d '\r\n')

    [[ "${found}" == "yes" ]]
}

script_dir=$(mktemp -d)
readonly script_dir
trap 'rm -rf "${script_dir}"' EXIT

install_font() {
    cat >"${script_dir}/install_font.ps1" <<'PWSH'
$ProgressPreference = 'SilentlyContinue'
$UserFontDir = "$env:LOCALAPPDATA\Microsoft\Windows\Fonts"
$RegPath = 'HKCU:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts'

Add-Type -AssemblyName System.Drawing
Add-Type -Name Native -Namespace Font -MemberDefinition @'
[DllImport("gdi32.dll", CharSet = CharSet.Unicode)]
public static extern int AddFontResourceW(string path);
[DllImport("user32.dll")]
public static extern int SendMessageTimeout(IntPtr hWnd, uint msg, IntPtr wParam,
    IntPtr lParam, uint flags, uint timeout, out IntPtr result);
'@

# Windows expects the value name "<GDI family><style> (TrueType)". The GDI family already
# carries non-standard weights (e.g. "JetBrainsMono NF ExtraBold"), so only Bold and
# Italic -- the two styles GDI models as flags rather than families -- get appended.
function Get-FontRegistryName($file) {
    $collection = New-Object System.Drawing.Text.PrivateFontCollection
    $collection.AddFontFile($file.FullName)
    $name = $collection.Families[0].Name
    $collection.Dispose()

    $variant = ($file.BaseName -split '-')[-1]
    if (($variant -replace 'Italic$', '') -eq 'Bold') { $name += ' Bold' }
    if ($variant.EndsWith('Italic')) { $name += ' Italic' }

    return "$name (TrueType)"
}

New-Item -ItemType Directory -Force -Path $UserFontDir | Out-Null
$fonts = @(Get-ChildItem -Path $UserFontDir -Filter 'JetBrainsMono*.ttf' -Recurse -ErrorAction SilentlyContinue)

if ($fonts.Count -eq 0) {
    Write-Host "Downloading JetBrainsMono Nerd Font (~200MB, one-time)..."
    $zip = "$env:TEMP\JetBrainsMono.zip"
    $extracted = "$env:TEMP\JetBrainsMono_nf"
    $url = 'https://github.com/ryanoasis/nerd-fonts/releases/latest/download/JetBrainsMono.zip'

    Invoke-WebRequest -Uri $url -OutFile $zip -UseBasicParsing
    Expand-Archive -Path $zip -DestinationPath $extracted -Force
    Get-ChildItem -Path $extracted -Filter '*.ttf' -Recurse | ForEach-Object {
        Copy-Item $_.FullName (Join-Path $UserFontDir $_.Name) -Force
    }
    Remove-Item $zip, $extracted -Recurse -Force -ErrorAction SilentlyContinue

    $fonts = @(Get-ChildItem -Path $UserFontDir -Filter 'JetBrainsMono*.ttf' -Recurse)
}

$registered = (Get-ItemProperty -Path $RegPath).PSObject.Properties | ForEach-Object { $_.Value }
$added = 0

foreach ($font in $fonts) {
    if ($registered -notcontains $font.FullName -and $registered -notcontains $font.Name) {
        New-ItemProperty -Path $RegPath -Name (Get-FontRegistryName $font) `
            -Value $font.FullName -PropertyType String -Force | Out-Null
        $added++
    }
    [void][Font.Native]::AddFontResourceW($font.FullName)
}

# Without this broadcast already-running apps keep their stale font list.
$result = [IntPtr]::Zero
[void][Font.Native]::SendMessageTimeout([IntPtr]0xffff, 0x001D, [IntPtr]::Zero,
    [IntPtr]::Zero, 2, 1000, [ref]$result)

Write-Host "Registered $added new font file(s); loaded $($fonts.Count) into the session."
PWSH

    powershell.exe -ExecutionPolicy Bypass -File "$(wslpath -w "${script_dir}")\\install_font.ps1"
}

# Rewriting these files wholesale would strip the comments VSCode and Windows Terminal
# settings are full of, so replace just the one value in place and refuse to guess when
# the key is missing or ambiguous.
set_json_leaf() {
    local path="$1" leaf="$2" value="$3"

    python3 - "${path}" "${leaf}" "${value}" <<'PYEOF'
import re
import sys

path, leaf, value = sys.argv[1], sys.argv[2], sys.argv[3]
text = open(path, encoding="utf-8-sig").read()
pattern = re.compile(rf'("{re.escape(leaf)}"\s*:\s*)"[^"]*"')

if len(pattern.findall(text)) != 1:
    sys.exit(1)

with open(path, "w", encoding="utf-8") as handle:
    handle.write(pattern.sub(lambda m: m.group(1) + f'"{value}"', text))
PYEOF
}

if font_is_available; then
    echo "${font_family} already installed and loaded, skipping..."
else
    install_font

    if font_is_available; then
        echo "${font_family} installed and loaded."
    else
        echo ">>> Font registered but not yet visible to Windows. Reboot to finish." >&2
    fi
fi

if [[ -f "${vscode_settings}" ]] && set_json_leaf "${vscode_settings}" "terminal.integrated.fontFamily" "${font_stack}"; then
    echo "VSCode terminal font set to '${font_stack}'"
else
    echo ""
    echo ">>> Could not update VSCode settings. Manually add to settings.json:"
    echo "    \"terminal.integrated.fontFamily\": \"${font_stack}\""
fi

shopt -s nullglob
wt_settings_files=(/mnt/c/Users/"${windows_username}"/AppData/Local/Packages/Microsoft.WindowsTerminal_*/LocalState/settings.json)
shopt -u nullglob

for wt_settings in "${wt_settings_files[@]}"; do
    if set_json_leaf "${wt_settings}" "face" "${font_family}"; then
        echo "Windows Terminal font set to '${font_family}'"
    else
        echo ""
        echo ">>> Could not update Windows Terminal settings. Manually set profiles.defaults.font.face:"
        echo "    \"face\": \"${font_family}\""
    fi
done
