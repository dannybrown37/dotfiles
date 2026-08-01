#!/usr/bin/env bash
set -euo pipefail

readonly MAX_ATTEMPTS=10
readonly RETRY_DELAY_SECONDS=0.2

tmpfile="/tmp/.tmux_clipboard_$$"
errfile="/tmp/.tmux_clipboard_err_$$"
trap 'rm -f "${tmpfile}" "${errfile}"' EXIT

cat >"${tmpfile}"
winpath=$(wslpath -w "${tmpfile}")

# Set-Clipboard intermittently throws "OpenClipboard failed" when another
# Windows process (clipboard history, antivirus, ...) briefly holds the
# clipboard lock. Retry through it instead of silently dropping the copy.
attempt=1
while ((attempt <= MAX_ATTEMPTS)); do
	if powershell.exe -NoProfile -Command \
		"Get-Content -Raw -Path '${winpath}' -Encoding UTF8 | Set-Clipboard" \
		2>"${errfile}"; then
		exit 0
	fi
	attempt=$((attempt + 1))
	sleep "${RETRY_DELAY_SECONDS}"
done

echo "tmux-copy-to-clipboard: clipboard write failed after ${MAX_ATTEMPTS} attempts" >&2
cat "${errfile}" >&2
exit 1
