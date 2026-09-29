#!/usr/bin/env bash
## @extra difft | Diff that understands syntax
set -euo pipefail

# shellcheck source=install/cargo_env.sh
source "$(dirname "${BASH_SOURCE[0]}")/../cargo_env.sh"

if ! command -v cargo &>/dev/null; then
    echo "difftastic needs cargo -- run 'just rust' first" >&2
    exit 1
fi

cargo install --locked difftastic
