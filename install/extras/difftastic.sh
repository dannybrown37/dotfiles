#!/usr/bin/env bash
## @extra difft | Diff that understands syntax
set -euo pipefail

# shellcheck source=install/versions.sh
source "$(dirname "${BASH_SOURCE[0]}")/../versions.sh"
# shellcheck source=install/release_binary.sh
source "$(dirname "${BASH_SOURCE[0]}")/../release_binary.sh"

install_release_binary difft \
    "https://github.com/Wilfred/difftastic/releases/download/${DIFFTASTIC_VERSION}/difft-${DIFFTASTIC_VERSION}-x86_64-unknown-linux-musl.tar.gz" \
    "${DIFFTASTIC_VERSION}"
