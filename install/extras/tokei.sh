#!/usr/bin/env bash
## @extra tokei | Count lines of code by language
set -euo pipefail

# shellcheck source=install/versions.sh
source "$(dirname "${BASH_SOURCE[0]}")/../versions.sh"

## v12 is the last release with pre-built binaries

if ! command -v tokei &>/dev/null; then
    tmp_dir=$(mktemp -d)
    curl -sLo "${tmp_dir}/tokei.tar.gz" \
        "https://github.com/XAMPPRocky/tokei/releases/download/v${TOKEI_VERSION}/tokei-x86_64-unknown-linux-gnu.tar.gz"
    tar -xf "${tmp_dir}/tokei.tar.gz" -C "${tmp_dir}"
    sudo install "${tmp_dir}/tokei" /usr/local/bin/tokei
    rm -rf "${tmp_dir}"
else
    echo "tokei is already installed on this system"
fi
