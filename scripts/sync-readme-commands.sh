#!/usr/bin/env bash

set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
README="${ROOT}/README.md"
ALIASES="${ROOT}/config/.bash_aliases"
BIN_DIR="${ROOT}/bin"
SCRIPTS_DIR="${ROOT}/scripts"

MARKER_START="<!-- @doc:commands:start -->"
MARKER_END="<!-- @doc:commands:end -->"

docs=""

while IFS= read -r line; do
    if [[ "$line" =~ ^[[:space:]]*alias[[:space:]]+([a-zA-Z0-9_-]+)=.*#[[:space:]]*@doc[[:space:]]+(.*) ]]; then
        name="${BASH_REMATCH[1]}"
        desc="${BASH_REMATCH[2]}"
        docs+="- \`${name}\`: ${desc}"$'\n'
    elif [[ "$line" =~ ^[[:space:]]*(function[[:space:]]+)?([a-zA-Z0-9_-]+)\(\).*#[[:space:]]*@doc[[:space:]]+(.*) ]]; then
        name="${BASH_REMATCH[2]}"
        desc="${BASH_REMATCH[3]}"
        docs+="- \`${name}\`: ${desc}"$'\n'
    fi
done < "$ALIASES"

for dir in "$BIN_DIR" "$SCRIPTS_DIR"; do
    [[ -d "$dir" ]] || continue
    for file in "$dir"/*; do
        [[ -f "$file" ]] || continue
        name=$(basename "$file" .sh)
        while IFS= read -r line; do
            if [[ "$line" =~ ^#[[:space:]]*@doc[[:space:]]+(.*) ]]; then
                desc="${BASH_REMATCH[1]}"
                docs+="- \`${name}\`: ${desc}"$'\n'
            fi
        done < "$file"
    done
done

docs=$(echo "$docs" | sort)

start_line=$(grep -n "$MARKER_START" "$README" | head -1 | cut -d: -f1)
end_line=$(grep -n "$MARKER_END" "$README" | head -1 | cut -d: -f1)

if [[ -z "$start_line" || -z "$end_line" ]]; then
    echo "ERROR: Missing $MARKER_START / $MARKER_END markers in README.md" >&2
    exit 1
fi

{
    head -n "$start_line" "$README"
    echo ""
    echo "$docs"
    tail -n +"$end_line" "$README"
} > "${README}.tmp"

if diff -q "$README" "${README}.tmp" > /dev/null 2>&1; then
    rm "${README}.tmp"
else
    mv "${README}.tmp" "$README"
    echo "README.md updated with @doc commands"
fi
