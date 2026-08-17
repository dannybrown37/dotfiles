#!/usr/bin/env bash
## @just 33 Developer Tools | Install spotify_player TUI (remote control, no audio)

##
## Install spotify_player (terminal Spotify client) + symlink its config
##
## Built controller-only: no `streaming` feature, so there is no librespot
## audio backend and no ALSA/PulseAudio plumbing (unreliable under WSL2).
## Playback happens on another Spotify Connect device — typically the Windows
## desktop app — and this drives it remotely. The `notify` feature is also
## omitted: it links against libdbus, which is both a build dependency we do
## not want and useless without a Linux desktop session.
##
## Requires a Spotify Premium account. After installing, run:
##   spotify_player authenticate
##

set -euo pipefail

readonly CRATE="spotify_player"
readonly FEATURES="image,fzf"
readonly USER_AGENT="dotfiles-install-script (https://github.com/dannybrown37/dotfiles)"

if ! command -v cargo &>/dev/null; then
    echo "cargo not found — run 'make rust' first" >&2
    exit 1
fi

for dep in curl jq; do
    command -v "${dep}" &>/dev/null || sudo apt-get install -y -qq "${dep}"
done

latest_version=$(curl -sS -H "User-Agent: ${USER_AGENT}" "https://crates.io/api/v1/crates/${CRATE}" |
    jq -r '.crate.max_stable_version')
current_version=$(spotify_player --version 2>/dev/null | awk '{print $2}' || echo "none")

if [[ -z "${latest_version}" || "${latest_version}" == "null" ]]; then
    echo "Could not determine latest ${CRATE} version from crates.io" >&2
    exit 1
fi

if [[ "${current_version}" == "${latest_version}" ]]; then
    echo "${CRATE} ${latest_version} already installed"
else
    echo "Installing ${CRATE} ${current_version} → ${latest_version} (features: ${FEATURES})"
    cargo install "${CRATE}" --locked --no-default-features --features "${FEATURES}"
    echo "${CRATE} ${latest_version} installed at $(command -v spotify_player)"
fi

##
## Symlink spotify_player config
##

# shellcheck source=install/link_config.sh
source "$(dirname "${BASH_SOURCE[0]}")/link_config.sh"

config_src="${HOME}/projects/dotfiles/config/spotify-player"

for config_file in app.toml keymap.toml; do
    link_config "${config_src}/${config_file}" \
        "${HOME}/.config/spotify-player/${config_file}"
done

##
## Authentication is interactive (opens a browser, catches the OAuth redirect
## on http://127.0.0.1:8989/login), so it is left to the user to run.
##

if [[ -f "${HOME}/.cache/spotify-player/user_client_token.json" ]]; then
    echo "spotify_player already authenticated"
else
    echo
    echo "Next step — authenticate (opens a browser, one time per machine):"
    echo "    spotify_player authenticate"
    echo
    echo "Then press 'D' in the TUI to pick a playback device (e.g. the Windows"
    echo "Spotify desktop app), since this build does not play audio itself."
fi
