#!/usr/bin/env bash
# fleet: run parallel Claude Code / Copilot agents and triage review requests.
# `uv run --project` uses the dotfiles venv (for Textual) without changing cwd,
# so `fleet new` still branches from the repo you are standing in.
set -euo pipefail

dotfiles_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHONPATH="${dotfiles_dir}/scripts${PYTHONPATH:+:${PYTHONPATH}}" \
    exec uv run --quiet --project "${dotfiles_dir}" python -m fleet "$@"
