#!/usr/bin/env bash
# Called by Claude Code and Copilot hooks: fleet-hook.sh <claude|copilot> <event>
# Runs for every agent session, so the fleet dashboard can show sessions it
# did not start. Never prints and always exits 0: Claude feeds some hooks'
# stdout to the model, and a failing hook must never get in an agent's way.
# python3 -S skips site-packages, which halves startup on every agent event.
set -uo pipefail
exec >/dev/null 2>&1

# Parameter expansion, not dirname: no fork, and no dependency on coreutils.
source_path="${BASH_SOURCE[0]}"
[[ "${source_path}" == */* ]] || source_path="./${source_path}"
scripts_dir="$(cd "${source_path%/*}" && pwd)"
PYTHONPATH="${scripts_dir}" python3 -S -m fleet.hook "$@"
exit 0
