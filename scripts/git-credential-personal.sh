#!/usr/bin/env bash

##
##  Git credential helper for repos that must always use the personal GitHub
##  account, even on a machine where GITHUB_TOKEN holds a work token.
##  Wired up via includeIf in config/.gitconfig -- see config/.gitconfig-personal.
##

set -euo pipefail

readonly GH_CREDENTIAL_HELPER=/usr/bin/gh

fall_back_to_gh() {
    if [[ -x "${GH_CREDENTIAL_HELPER}" ]]; then
        exec "${GH_CREDENTIAL_HELPER}" auth git-credential "$@"
    fi
    exit 0
}

# Only the "get" operation returns credentials; store/erase are no-ops here
# because the token comes from the environment, not a saved credential.
if [[ "${1:-}" != "get" ]]; then
    exit 0
fi

if [[ -z "${MY_GITHUB_TOKEN:-}" ]]; then
    fall_back_to_gh "$@"
fi

echo "username=${MY_GITHUB_USER:-dannybrown37}"
echo "password=${MY_GITHUB_TOKEN}"
