#!/usr/bin/env bash
## @extra git-absorb | Auto-fixup commits to the right place

set -euo pipefail

# shellcheck source=install/versions.sh
source "$(dirname "${BASH_SOURCE[0]}")/../versions.sh"
# shellcheck source=install/release_binary.sh
source "$(dirname "${BASH_SOURCE[0]}")/../release_binary.sh"

install_release_binary git-absorb \
    "https://github.com/tummychow/git-absorb/releases/download/${GIT_ABSORB_VERSION}/git-absorb-${GIT_ABSORB_VERSION}-x86_64-unknown-linux-musl.tar.gz"
