#!/usr/bin/env bash
set -euo pipefail
tmpfile="/tmp/.tmux_clipboard_$$"
cat > "$tmpfile"
wslpath=$(wslpath -w "$tmpfile")
powershell.exe -NoProfile -Command "Get-Content -Raw -Path '${wslpath}' -Encoding UTF8 | Set-Clipboard" 2>/dev/null
rm -f "$tmpfile"
