#!/usr/bin/env bash

set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
SKIP_DIRS=".git .github .vscode .pytest_cache .ruff_cache"

exit_code=0

for dir in "$ROOT"/*/; do
    name=$(basename "$dir")

    skip=false
    for s in $SKIP_DIRS; do
        [[ "$name" == "$s" ]] && skip=true && break
    done
    $skip && continue

    if [[ ! -f "${dir}.dirdesc" ]]; then
        echo "ERROR: ${name}/ is missing a .dirdesc file" >&2
        exit_code=1
    elif [[ ! -s "${dir}.dirdesc" ]]; then
        echo "ERROR: ${name}/.dirdesc is empty" >&2
        exit_code=1
    fi
done

exit $exit_code
