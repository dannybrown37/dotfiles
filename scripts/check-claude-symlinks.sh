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

# .claude/ holds the real files; .github/ mirrors them with symlinks so Copilot
# reads the same content Claude does.
check_symlink ".github/copilot-instructions.md" ".claude/CLAUDE.md"

if [[ -L ".claude/CLAUDE.md" || ! -f ".claude/CLAUDE.md" ]]; then
    echo "ERROR: .claude/CLAUDE.md should be a real file, not a symlink" >&2
    exit_code=1
fi

for dir in .claude/skills/*/; do
    name=$(basename "$dir")
    check_symlink ".github/skills/${name}" "${dir%/}"
done

for entry in .github/skills/*; do
    name=$(basename "$entry")
    if [[ ! -d ".claude/skills/${name}" ]]; then
        echo "ERROR: .github/skills/${name} has no matching .claude/skills/${name} source" >&2
        exit_code=1
    fi
done

exit $exit_code
