#!/usr/bin/env bash
## @extra jless | Pager for JSON
set -euo pipefail

# shellcheck source=install/cargo_env.sh
source "$(dirname "${BASH_SOURCE[0]}")/../cargo_env.sh"

if ! command -v cargo &>/dev/null; then
    echo "jless needs cargo -- run 'just rust' first" >&2
    exit 1
fi

# jless links against libxcb for clipboard support
sudo apt install -y libxcb-render0-dev libxcb-shape0-dev libxcb-xfixes0-dev

cargo install --locked jless
