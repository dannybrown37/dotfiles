#!/usr/bin/env bash
## @extra htmlq | jq for HTML
set -euo pipefail

# shellcheck source=install/versions.sh
source "$(dirname "${BASH_SOURCE[0]}")/../versions.sh"
# shellcheck source=install/release_binary.sh
source "$(dirname "${BASH_SOURCE[0]}")/../release_binary.sh"

install_release_binary htmlq \
    "https://github.com/mgdm/htmlq/releases/download/v${HTMLQ_VERSION}/htmlq-x86_64-linux.tar.gz" \
    "${HTMLQ_VERSION}"
