#!/usr/bin/env bash
## @extra jless | Pager for JSON
set -euo pipefail

# shellcheck source=install/versions.sh
source "$(dirname "${BASH_SOURCE[0]}")/../versions.sh"

if command -v jless &>/dev/null; then
    echo "jless is already installed on this system"
    exit 0
fi

# The release binary links libxcb for clipboard support.
sudo apt install -y libxcb-render0 libxcb-shape0 libxcb-xfixes0

# Shipped as a zip, which install_release_binary cannot unpack.
tmp_dir=$(mktemp -d)
trap 'rm -rf "${tmp_dir}"' EXIT
curl -fsSLo "${tmp_dir}/jless.zip" \
    "https://github.com/PaulJuliusMartinez/jless/releases/download/v${JLESS_VERSION}/jless-v${JLESS_VERSION}-x86_64-unknown-linux-gnu.zip"
unzip -q "${tmp_dir}/jless.zip" -d "${tmp_dir}"
sudo install "${tmp_dir}/jless" /usr/local/bin/jless
echo "jless installed at $(command -v jless)"
