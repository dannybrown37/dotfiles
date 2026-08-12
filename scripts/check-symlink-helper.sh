#!/usr/bin/env bash
# Blocks a raw `ln -s` in an install script. Config symlinks go through
# link_config, which refuses to clobber a hand-written file and is idempotent
# on a re-run -- a bare `ln -s` is neither, and that pile of "File exists"
# errors is what the helper was written to end.
#
# The file that defines link_config is exempt, found by grepping for the
# definition so the exemption survives a rename. A genuine non-config symlink
# (a root-owned system path, say) opts out per line with a trailing
# `# allow-raw-symlink: <why>`.

set -euo pipefail
shopt -s nullglob

readonly install_dir="${1:-$(git rev-parse --show-toplevel)/install}"
readonly marker='allow-raw-symlink'
readonly symlink_re='(^|[[:space:];&|(])ln[[:space:]]+(-[[:alnum:]]*s[[:alnum:]]*|--symbolic)([[:space:]]|$)'

if [[ ! -d "${install_dir}" ]]; then
    echo "check-symlink-helper: not a directory: ${install_dir}" >&2
    exit 2
fi

readarray -t helpers < <(
    grep -lE '^[[:space:]]*link_config[[:space:]]*\(\)' "${install_dir}"/*.sh || true
)

found=0

for file in "${install_dir}"/*.sh; do
    for helper in "${helpers[@]}"; do
        [[ "${file}" == "${helper}" ]] && continue 2
    done

    while IFS=: read -r lineno line; do
        [[ "${line}" == *"${marker}"* ]] && continue
        # Prose describing `ln -s` in a comment is not a call. A `#` inside a
        # string would also truncate here; install scripts don't have one.
        [[ "${line%%#*}" =~ ${symlink_re} ]] || continue

        echo "BLOCKED: ${file}:${lineno} creates a symlink directly:" >&2
        echo "  ${line#"${line%%[![:space:]]*}"}" >&2
        found=1
    done < <(grep -nE "${symlink_re}" "${file}" || true)
done

if [[ "${found}" -eq 1 ]]; then
    echo "Use link_config \"\${src}\" \"\${dest}\" instead, or mark the line" >&2
    echo "  # ${marker}: <why this one is not a config symlink>" >&2
    exit 1
fi

exit 0
