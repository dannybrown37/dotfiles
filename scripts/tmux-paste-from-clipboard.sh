#!/usr/bin/env bash
set -euo pipefail
powershell.exe -NoProfile -Command '[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; Get-Clipboard' 2>/dev/null | tr -d '\r'
