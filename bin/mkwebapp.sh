mkwebapp() {  # @doc Create a Chrome --app= shortcut on the Windows Desktop | mkwebapp <name> <url> [--taskbar]
    if [[ $# -lt 2 ]]; then
        echo "Usage: mkwebapp <name> <url> [--taskbar]"
        echo "  --taskbar  Attempt to pin to taskbar (best-effort on Win10/11)"
        return 1
    fi

    local name="$1"
    local url="$2"
    local pin_taskbar=false

    [[ "$url" != http://* && "$url" != https://* ]] && url="https://$url"

    for arg in "${@:3}"; do
        [[ "$arg" == "--taskbar" ]] && pin_taskbar=true
    done

    powershell.exe -NoProfile -Command "
        \$chromePaths = @(
            \"\$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe\",
            \"\$env:PROGRAMFILES\Google\Chrome\Application\chrome.exe\",
            \"\${env:PROGRAMFILES(X86)}\Google\Chrome\Application\chrome.exe\"
        )
        \$chrome = \$chromePaths | Where-Object { Test-Path \$_ } | Select-Object -First 1
        if (-not \$chrome) { Write-Error 'Chrome not found'; exit 1 }

        \$ws      = New-Object -ComObject WScript.Shell
        \$desktop = \$ws.SpecialFolders('Desktop')
        \$path    = Join-Path \$desktop '${name}.lnk'

        \$sc = \$ws.CreateShortcut(\$path)
        \$sc.TargetPath   = \$chrome
        \$sc.Arguments    = '--app=${url}'
        \$sc.IconLocation = \"\$chrome, 0\"
        \$sc.WindowStyle  = 1
        \$sc.Save()

        Write-Host \"✓ Desktop shortcut: \$path\"

        if (\$${pin_taskbar}) {
            try {
                \$shell  = New-Object -ComObject Shell.Application
                \$folder = \$shell.Namespace([System.IO.Path]::GetDirectoryName(\$path))
                \$item   = \$folder.ParseName([System.IO.Path]::GetFileName(\$path))
                \$verb   = \$item.Verbs() | Where-Object { \$_.Name -match 'Pin to taskbar' }
                if (\$verb) {
                    \$verb.DoIt()
                    Write-Host '✓ Pinned to taskbar'
                } else {
                    Write-Host '⚠ Pin verb unavailable — right-click the shortcut to pin manually'
                }
            } catch {
                Write-Host \"⚠ Taskbar pin failed: \$_\"
            }
        }
    "
}
