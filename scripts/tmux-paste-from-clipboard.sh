#!/usr/bin/env bash
set -euo pipefail

if command -v win32yank.exe &>/dev/null; then
    win32yank.exe -o --lf
    exit 0
fi

readonly MAX_ATTEMPTS=10
readonly RETRY_DELAY_SECONDS=0.2

outfile="/tmp/.tmux_clipboard_paste_$$"
errfile="/tmp/.tmux_clipboard_paste_err_$$"
trap 'rm -f "${outfile}" "${errfile}"' EXIT

attempt=1
while ((attempt <= MAX_ATTEMPTS)); do
    if powershell.exe -NoProfile -Command \
        '[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; Get-Clipboard' \
        >"${outfile}" 2>"${errfile}"; then
        tr -d '\r' <"${outfile}"
        exit 0
    fi
    attempt=$((attempt + 1))
    sleep "${RETRY_DELAY_SECONDS}"
done

echo "tmux-paste-from-clipboard: clipboard read failed after ${MAX_ATTEMPTS} attempts" >&2
cat "${errfile}" >&2
exit 1
