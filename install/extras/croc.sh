#!/usr/bin/env bash
## @extra croc | Send files between machines securely
set -euo pipefail

# A pinned release, not getcroc.schollz.com: that script asks api.github.com
# for the latest tag unauthenticated, which shared CI runner IPs get 403'd on.
# shellcheck source=install/versions.sh
source "$(dirname "${BASH_SOURCE[0]}")/../versions.sh"
# shellcheck source=install/release_binary.sh
source "$(dirname "${BASH_SOURCE[0]}")/../release_binary.sh"

install_release_binary croc \
    "https://github.com/schollz/croc/releases/download/v${CROC_VERSION}/croc_v${CROC_VERSION}_Linux-64bit.tar.gz" \
    "${CROC_VERSION}"
