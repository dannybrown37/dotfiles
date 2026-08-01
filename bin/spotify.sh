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
