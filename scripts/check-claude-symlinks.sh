#!/usr/bin/env bash

set -euo pipefail
shopt -s nullglob

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"

exit_code=0

check_symlink() {
    local link=$1 target=$2

    if [[ ! -e "$link" ]]; then
        echo "ERROR: ${link} is missing" >&2
        exit_code=1
        return
    fi
    if [[ ! -L "$link" ]]; then
        echo "ERROR: ${link} is not a symlink (should link to ${target})" >&2
        exit_code=1
        return
    fi
    if [[ "$(readlink -f "$link")" != "$(readlink -f "$target")" ]]; then
        echo "ERROR: ${link} does not resolve to ${target}" >&2
        exit_code=1
    fi
}

check_symlink ".claude/CLAUDE.md" ".github/copilot-instructions.md"

for dir in .github/skills/*/; do
    name=$(basename "$dir")
    check_symlink ".claude/skills/${name}" "${dir%/}"
done

for entry in .claude/skills/*/; do
    name=$(basename "$entry")
    if [[ ! -d ".github/skills/${name}" ]]; then
        echo "ERROR: .claude/skills/${name} has no matching .github/skills/${name} source" >&2
        exit_code=1
    fi
done

exit $exit_code
