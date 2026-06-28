#!/usr/bin/env bash

set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
README="${ROOT}/README.md"

MARKER_START="<!-- @doc:structure:start -->"
MARKER_END="<!-- @doc:structure:end -->"

docs=""

for dir in "$ROOT"/*/; do
    [[ -f "${dir}.dirdesc" ]] || continue
    name=$(basename "$dir")
    desc=$(head -1 "${dir}.dirdesc")
    docs+="| \`${name}/\` | ${desc} |"$'\n'
done

docs=$(printf "%s" "$docs" | sort)

start_line=$(grep -n "$MARKER_START" "$README" | head -1 | cut -d: -f1)
end_line=$(grep -n "$MARKER_END" "$README" | head -1 | cut -d: -f1)

if [[ -z "$start_line" || -z "$end_line" ]]; then
    echo "ERROR: Missing $MARKER_START / $MARKER_END markers in README.md" >&2
    exit 1
fi

{
    head -n "$start_line" "$README"
    echo "| Directory | Description |"
    echo "| --- | --- |"
    echo "$docs"
    echo ""
    tail -n +"$end_line" "$README"
} > "${README}.tmp"

if diff -q "$README" "${README}.tmp" > /dev/null 2>&1; then
    rm "${README}.tmp"
else
    mv "${README}.tmp" "$README"
    echo "README.md updated with directory structure"
fi
