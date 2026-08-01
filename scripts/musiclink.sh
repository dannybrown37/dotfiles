#!/usr/bin/env bash

##
## Convert a music link (Spotify, YouTube, Apple Music, ...) into a
## service-agnostic link that lets the recipient open it in their own
## streaming service, via the Odesli/song.link API.
##
## Usage: musiclink.sh <url>
##

set -euo pipefail

readonly EXIT_USAGE=2
readonly API_BASE="https://api.song.link/v1-alpha.1/links"

usage() {
    echo "Usage: musiclink.sh <url>" >&2
}

die() {
    echo "musiclink: $1" >&2
    exit 1
}

main() {
    if [[ $# -ne 1 ]]; then
        usage
        exit "${EXIT_USAGE}"
    fi

    for dep in curl jq; do
        command -v "${dep}" &>/dev/null || die "${dep} is required but not installed"
    done

    local input_url="$1"
    local encoded_url
    encoded_url=$(jq -rn --arg v "${input_url}" '$v|@uri')

    local response http_status body
    if ! response=$(curl -sS -w '\n%{http_code}' "${API_BASE}?url=${encoded_url}"); then
        die "curl request to song.link failed"
    fi
    http_status="${response##*$'\n'}"
    body="${response%$'\n'*}"

    if [[ "${http_status}" != 2* ]]; then
        die "song.link returned HTTP ${http_status}: ${body}"
    fi

    local page_url
    page_url=$(jq -r '.pageUrl // empty' <<<"${body}")
    if [[ -z "${page_url}" ]]; then
        die "response did not contain a pageUrl: ${body}"
    fi

    echo "${page_url}"
}

main "$@"
