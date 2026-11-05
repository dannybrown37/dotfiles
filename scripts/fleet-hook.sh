#!/usr/bin/env bash
# Called by Claude Code and Copilot hooks: fleet-hook.sh <claude|copilot> <event>
# Runs for every agent session, so the fleet dashboard can show sessions it
# did not start. Never prints and always exits 0: Claude feeds some hooks'
# stdout to the model, and a failing hook must never get in an agent's way.
# python3 -S skips site-packages, which halves startup on every agent event.
set -uo pipefail

scripts_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHONPATH="${scripts_dir}" python3 -S -m fleet.hook "$@" >/dev/null 2>&1
exit 0
