#!/usr/bin/env bash
## Install git-absorb (auto-fixup commits to the right place)

set -euo pipefail

# shellcheck source=install/cargo_env.sh
source "$(dirname "${BASH_SOURCE[0]}")/cargo_env.sh"

if ! command -v cargo &>/dev/null; then
    echo "git-absorb needs cargo -- run 'make rust' first" >&2
    # shellcheck disable=SC2317  # reachable when executed rather than sourced
    return 1 2>/dev/null || exit 1
fi

if command -v git-absorb &>/dev/null; then
    echo "git-absorb already installed: $(git-absorb --version)"
else
    cargo install git-absorb
    echo "git-absorb installed: $(git-absorb --version)"
fi
