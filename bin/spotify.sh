## Spotify CLI helpers -- talk to spotify_player's client socket directly
## (it starts a lightweight client on demand), no TUI window required.

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

    command -v spotify_player &>/dev/null || {
        echo "spotify_copy_playing_link: spotify_player not found" >&2
        return 1
    }

    local playback
    playback=$(spotify_player get key playback 2>&1) || {
        echo "spotify_copy_playing_link: spotify_player get key playback failed: ${playback}" >&2
        return 1
    }

    local link
    link=$(jq -r '.item.external_urls.spotify // empty' <<<"${playback}")
    if [[ -z "${link}" ]]; then
        echo "spotify_copy_playing_link: no track currently playing" >&2
        return 1
    fi

    if [[ "${convert_to_musiclink}" -eq 1 ]]; then
        link=$("${DOTFILES_DIR}/scripts/musiclink.sh" "${link}") || return 1
    fi

    printf '%s' "${link}" | "${DOTFILES_DIR}/scripts/tmux-copy-to-clipboard.sh"
    echo "Copied: ${link}"
}
