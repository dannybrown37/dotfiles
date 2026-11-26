#!/usr/bin/env bash
# shellcheck disable=SC2034

##
## Retry flags for every download under install/. A runner (or Wi-Fi) that
## resets one connection should not fail a whole install: the weekly Extras
## run lost git-a-grip to a single "Connection reset by peer" from astral.sh.
##
## Library only -- no `## @just` header.
##

CURL_RETRY=(--retry 3 --retry-all-errors --retry-delay 2)

##
## curl_buffered <curl args...>
## curl with CURL_RETRY, but the body goes to a temp file and is printed only
## once the download is whole. Use it wherever curl feeds a pipe: curl cannot
## take back bytes a failed attempt already wrote to stdout, so a plain retry
## into `| sh` could run half an installer and then the full one.
##
curl_buffered() {
    local tmp rc=0
    tmp="$(mktemp)"
    if curl "${CURL_RETRY[@]}" "$@" -o "${tmp}"; then
        cat "${tmp}"
    else
        rc=$?
    fi
    rm -f "${tmp}"
    return "${rc}"
}
