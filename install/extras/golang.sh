#!/usr/bin/env bash
set -euo pipefail
## @extra go | Go toolchain (pinned version)
## @runtime

# shellcheck source=install/versions.sh
source "$(dirname "${BASH_SOURCE[0]}")/../versions.sh"

target_version="go${GOLANG_VERSION}"
current_version=$(go version 2>/dev/null | awk '{print $3}' || true)

if [[ "${current_version}" == "${target_version}" ]]; then
    echo "Go ${target_version} already installed"
    exit 0
fi

echo "Installing Go: ${current_version:-none} → ${target_version}"
tmp_dir=$(mktemp -d)
trap 'rm -rf "${tmp_dir}"' EXIT
curl -fsSLo "${tmp_dir}/go.tar.gz" "https://go.dev/dl/${target_version}.linux-amd64.tar.gz"
sudo rm -rf /usr/local/go
sudo tar -xzf "${tmp_dir}/go.tar.gz" -C /usr/local
/usr/local/go/bin/go version
