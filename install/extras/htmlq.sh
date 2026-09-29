#!/usr/bin/env bash
## @extra htmlq | jq for HTML
set -euo pipefail

# shellcheck source=install/cargo_env.sh
source "$(dirname "${BASH_SOURCE[0]}")/../cargo_env.sh"

if ! command -v cargo &>/dev/null; then
    echo "htmlq needs cargo -- run 'just rust' first" >&2
    exit 1
fi

cargo install --locked htmlq
