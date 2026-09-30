#!/usr/bin/env bash
## @extra cartoon | Compress noisy CLI output for AI agents
##
## Install the latest version of cartoon and wire up its hook
## https://github.com/abhijitbansal/cartoon
##

set -euo pipefail

# shellcheck source=install/cargo_env.sh
source "$(dirname "${BASH_SOURCE[0]}")/../cargo_env.sh"

cargo install cartoon --locked

echo "cartoon $(cartoon --version | awk '{print $2}') installed at $(command -v cartoon)"
