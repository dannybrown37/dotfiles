#!/usr/bin/env bash
## Install git-branchless (stacked-diff workflow + smartlog)

set -euo pipefail

# shellcheck source=install/cargo_env.sh
source "$(dirname "${BASH_SOURCE[0]}")/cargo_env.sh"

if ! command -v cargo &>/dev/null; then
    echo "git-branchless needs cargo -- run 'make rust' first" >&2
    # shellcheck disable=SC2317  # reachable when executed rather than sourced
    return 1 2>/dev/null || exit 1
fi

if command -v git-branchless &>/dev/null; then
    echo "git-branchless already installed: $(git-branchless --version)"
else
    cargo install --locked git-branchless
    echo "git-branchless installed: $(git-branchless --version)"
fi

dotfiles_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -d "${dotfiles_dir}/.git" ]]; then
    git -C "${dotfiles_dir}" branchless init --main-branch main
fi
