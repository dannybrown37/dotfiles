#!/usr/bin/env bash

set -euo pipefail

readonly root="${DOTFILES_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"

failures=0

check_syntax() {
    local file="$1"
    if ! bash -n "$file" 2>&1; then
        ((failures++))
    fi
}

check_shellcheck() {
    local file="$1"
    if ! shellcheck --external-sources "$file" 2>&1; then
        ((failures++))
    fi
}

for dir in bin install scripts; do
    for file in "${root}/${dir}"/*.sh; do
        [[ -f "$file" ]] || continue
        check_syntax "$file"
        check_shellcheck "$file"
    done
done

if ((failures > 0)); then
    echo "FAIL: ${failures} issue(s) found"
    exit 1
else
    echo "OK: all shell scripts pass syntax and shellcheck"
fi
