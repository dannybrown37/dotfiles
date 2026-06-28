#!/usr/bin/env bash

set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
README="${ROOT}/README.md"
BIN_DIR="${ROOT}/bin"
SCRIPTS_DIR="${ROOT}/scripts"

MARKER_START="<!-- @doc:commands:start -->"
MARKER_END="<!-- @doc:commands:end -->"

docs=""

scan_sourced_file() {
    local filepath="$1"
    local source_label="$2"

    while IFS= read -r line; do
        if [[ "$line" =~ ^[[:space:]]*alias[[:space:]]+([a-zA-Z0-9_-]+)=.*#[[:space:]]*@doc[[:space:]]+(.*) ]]; then
            local name="${BASH_REMATCH[1]}"
            local desc="${BASH_REMATCH[2]}"
            docs+="| \`${name}\` | ${desc} | \`${source_label}\` |"$'\n'
        elif [[ "$line" =~ ^[[:space:]]*(function[[:space:]]+)?([a-zA-Z0-9_-]+)\(\).*#[[:space:]]*@doc[[:space:]]+(.*) ]]; then
            local name="${BASH_REMATCH[2]}"
            local desc="${BASH_REMATCH[3]}"
            docs+="| \`${name}\` | ${desc} | \`${source_label}\` |"$'\n'
        fi
    done < "$filepath"
}

scan_sourced_file "${ROOT}/config/.bash_aliases" "config/.bash_aliases"
scan_sourced_file "${ROOT}/config/.bashrc" "config/.bashrc"

for dir in "$BIN_DIR" "$SCRIPTS_DIR"; do
    [[ -d "$dir" ]] || continue
    for file in "$dir"/*; do
        [[ -f "$file" ]] || continue
        local_name=$(basename "$file" .sh)
        source_label="${dir#"${ROOT}"/}/$(basename "$file")"
        while IFS= read -r line; do
            if [[ "$line" =~ ^#[[:space:]]*@doc[[:space:]]+(.*) ]]; then
                desc="${BASH_REMATCH[1]}"
                docs+="| \`${local_name}\` | ${desc} | \`${source_label}\` |"$'\n'
            fi
        done < "$file"
    done
done

AHK_DIR="${ROOT}/ahk"
if [[ -d "$AHK_DIR" ]]; then
    for file in "$AHK_DIR"/*.ahk; do
        [[ -f "$file" ]] || continue
        source_label="ahk/$(basename "$file")"
        while IFS= read -r line; do
            if [[ "$line" =~ ^";"[[:space:]]*"@doc"[[:space:]]+(.*) ]]; then
                local_name="${BASH_REMATCH[1]%%:*}"
                desc="${BASH_REMATCH[1]#*: }"
                docs+="| \`${local_name}\` | ${desc} | \`${source_label}\` |"$'\n'
            fi
        done < "$file"
    done
fi

docs=$(echo "$docs" | sort | sed '/^$/d')

start_line=$(grep -n "$MARKER_START" "$README" | head -1 | cut -d: -f1)
end_line=$(grep -n "$MARKER_END" "$README" | head -1 | cut -d: -f1)

if [[ -z "$start_line" || -z "$end_line" ]]; then
    echo "ERROR: Missing $MARKER_START / $MARKER_END markers in README.md" >&2
    exit 1
fi

{
    head -n "$start_line" "$README"
    echo ""
    echo "| Command | Description | Source |"
    echo "| --- | --- | --- |"
    printf "%s" "$docs"
    echo ""
    tail -n +"$end_line" "$README"
} > "${README}.tmp"

if diff -q "$README" "${README}.tmp" > /dev/null 2>&1; then
    rm "${README}.tmp"
else
    mv "${README}.tmp" "$README"
    echo "README.md updated with @doc commands"
fi
