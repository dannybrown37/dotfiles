#!/usr/bin/env bash

# Get autohotkey files from this repo in WSL2, start in Windows environment
# May need to Powershell Admin run: `Set-ExecutionPolicy RemoteSigned`

set -euo pipefail

usage() {
    cat <<'EOF'
Usage: ahk [command]

  (none)     Start ahk/main.ahk (restarts it if already running)
  help       Browse ,, hotstrings with fzf
  open       Edit hotstrings.ahk
  secrets    Edit secrets.ahk
  kill       Stop every running AutoHotkey process
  startup    Start main.ahk at Windows login (one-time setup)
  -h, --help Show this help
EOF
}

if [[ -z "${ON_WINDOWS:-}" ]]; then
    echo "AHK is only available from WSL" >&2
    exit 1
fi

if [[ -z "${DOTFILES_DIR:-}" ]]; then
    echo "Something went wrong with your .bashrc, no value for DOTFILES_DIR" >&2
    exit 1
fi

# shellcheck source=../install/versions.sh
source "${DOTFILES_DIR}/install/versions.sh"

readonly ahk_dir="${DOTFILES_DIR}/ahk"
readonly hotstrings_path="${ahk_dir}/hotstrings.ahk"
readonly ahk_secrets_path="${ahk_dir}/secrets.ahk"
readonly main_path="${ahk_dir}/main.ahk"
readonly autocorrect_path="${ahk_dir}/vendor/AutoCorrectHotstrings.ahk"
readonly autocorrect_url="https://raw.githubusercontent.com/kunkel321/AutoCorrect2/${AHK_AUTOCORRECT_SHA}/Core/AutoCorrectHotstrings.ahk"

# The list has no license, so it's fetched per machine rather than committed.
fetch_autocorrect() {
    [[ -s "${autocorrect_path}" ]] && return
    mkdir -p "$(dirname "${autocorrect_path}")"
    echo "Fetching AutoCorrect list (${AHK_AUTOCORRECT_SHA:0:7})"
    curl -fsSL "${autocorrect_url}" -o "${autocorrect_path}.tmp"
    mv "${autocorrect_path}.tmp" "${autocorrect_path}"
}

start_main() {
    fetch_autocorrect
    echo "Starting ${main_path}"
    powershell.exe -Command "Start-Process '$(wslpath -w -a "${main_path}")'" 2>/dev/null
}

install_startup_shortcut() {
    local startup_dir
    startup_dir=$(powershell.exe -NoProfile -Command '[Environment]::GetFolderPath("Startup")' | tr -d '\r')
    powershell.exe -NoProfile -Command "
        \$shortcut = (New-Object -ComObject WScript.Shell).CreateShortcut('${startup_dir}\\dotfiles-ahk.lnk')
        \$shortcut.TargetPath = '$(wslpath -w -a "${main_path}")'
        \$shortcut.Save()"
    echo "main.ahk will start at login (${startup_dir}\\dotfiles-ahk.lnk)"
}

if [[ ! -e "${ahk_secrets_path}" ]]; then
    echo "; Private hotstrings, e.g. ::,,myemail::me@example.com" >>"${ahk_secrets_path}"
fi

case "${1:-}" in
    -h | --help) usage ;;
    help) grep -oE '^:[^:]*:,,[^:]+::.+' "${hotstrings_path}" | sed -E 's/^:[^:]*://' | fzf --sort ;;
    open) nvim "${hotstrings_path}" || code "${hotstrings_path}" ;;
    secrets) nvim "${ahk_secrets_path}" || code "${ahk_secrets_path}" ;;
    kill)
        for pid in $(powershell.exe -Command "Get-Process AutoHotkey* | Select-Object -ExpandProperty Id" | tr -d '\r'); do
            echo "Stopping ${pid}"
            powershell.exe -Command "Stop-Process -Id ${pid} -Force"
        done
        ;;
    startup) install_startup_shortcut ;;
    "") start_main ;;
    *)
        usage >&2
        exit 1
        ;;
esac
