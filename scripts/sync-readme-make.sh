#!/usr/bin/env bash
# Sync the `make help` output into README.md between code fence markers.

set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
README="${ROOT}/README.md"

make_output=$(make --no-print-directory -C "$ROOT" help)

# Extract everything before and after the code block
header="The output of \`make\` in the root directory:"
start_line=$(grep -n "$header" "$README" | head -1 | cut -d: -f1)
fence_start=$(awk -v s="$start_line" 'NR > s && /^```txt$/ { print NR; exit }' "$README")
fence_end=$(awk -v s="$fence_start" 'NR > s && /^```$/ { print NR; exit }' "$README")

# Rebuild the file
{
    head -n "$fence_start" "$README"
    echo "$make_output"
    tail -n +"$fence_end" "$README"
} > "${README}.tmp"

if diff -q "$README" "${README}.tmp" > /dev/null 2>&1; then
    rm "${README}.tmp"
else
    mv "${README}.tmp" "$README"
    echo "README.md updated with current make output"
fi
