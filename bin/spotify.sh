## Spotify CLI helpers -- talk to spotify_player's client socket directly
## (it starts a lightweight client on demand), no TUI window required.

_spotify_playback_json() {
    command -v spotify_player &>/dev/null || {
        echo "spotify: spotify_player not found" >&2
        return 1
    }

    local playback
    playback=$(spotify_player get key playback 2>&1) || {
        echo "spotify: spotify_player get key playback failed: ${playback}" >&2
        return 1
    }

    if [[ -z "$(jq -r '.item // empty' <<<"${playback}")" ]]; then
        echo "spotify: no track currently playing" >&2
        return 1
    fi

    printf '%s' "${playback}"
}

spotify_copy_playing_link() {
    local convert_to_musiclink=0
    case "${1:-}" in
        -m | --musiclink) convert_to_musiclink=1 ;;
        "") ;;
        *)
            echo "Usage: spotify_copy_playing_link [-m|--musiclink]" >&2
            return 2
            ;;
    esac

    local playback
    playback=$(_spotify_playback_json) || return 1

    local link
    link=$(jq -r '.item.external_urls.spotify' <<<"${playback}")

    if [[ "${convert_to_musiclink}" -eq 1 ]]; then
        link=$("${DOTFILES_DIR}/scripts/musiclink.sh" "${link}") || return 1
    fi

    printf '%s' "${link}" | "${DOTFILES_DIR}/scripts/tmux-copy-to-clipboard.sh"
    echo "${link}"
}

spotify_player_jump() {
    local session="${SPOTIFY_TMUX_SESSION:-Session}"
    local window="${SPOTIFY_TMUX_WINDOW:-spotify}"
    local index="${SPOTIFY_TMUX_WINDOW_INDEX:-9}"
    local target="${session}:${index}"

    tmux has-session -t "${session}" 2>/dev/null || tmux new-session -d -s "${session}"

    if ! tmux list-windows -t "${session}" -F '#{window_index}' | grep -qx "${index}"; then
        # new-window refuses to run if the index is already taken, so this
        # never clobbers an unrelated window sitting at that slot.
        tmux new-window -d -t "${target}" -n "${window}" 'spotify_player'
    fi

    # Enforced unconditionally, not just on creation -- a window already
    # sitting at this index (e.g. from before this fix) would otherwise
    # keep whatever name/rename settings it already had. automatic-rename
    # off stops tmux's own heuristic renaming, but allow-rename (separately)
    # governs whether an OSC title escape sequence from the running program
    # can still rename the window -- both need to be off, or it drifts back
    # to the launch directory's name once spotify_player (or its shell)
    # sets a title.
    tmux set-window-option -t "${target}" automatic-rename off
    tmux set-window-option -t "${target}" allow-rename off
    tmux rename-window -t "${target}" "${window}"

    tmux select-window -t "${target}"

    # select-window only updates the session's active window; if the
    # terminal's tmux client is attached to a different session (or a
    # different window's copy-mode view), it won't redraw on its own -- so
    # explicitly switch every attached client into this window too.
    local client
    while IFS= read -r client; do
        [[ -n "${client}" ]] && tmux switch-client -c "${client}" -t "${target}"
    done < <(tmux list-clients -F '#{client_name}')
}

alias spj='spotify_player_jump'

spotify_now_playing_markdown() {
    local playback
    playback=$(_spotify_playback_json) || return 1

    local title artist link
    title=$(jq -r '.item.name' <<<"${playback}")
    artist=$(jq -r '[.item.artists[].name] | join(", ")' <<<"${playback}")
    link=$(jq -r '.item.external_urls.spotify' <<<"${playback}")
    link=$("${DOTFILES_DIR}/scripts/musiclink.sh" "${link}") || return 1

    local markdown="Song On Right Now: \"[${title}](${link})\" by ${artist}"
    printf '%s' "${markdown}" | "${DOTFILES_DIR}/scripts/tmux-copy-to-clipboard.sh"
    echo "${markdown}"
}
