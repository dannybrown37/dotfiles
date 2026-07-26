#!/usr/bin/env bash

set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"

# The list of what to sync lives inside the store, not in this repo.
readonly MANIFEST="manifest"

die() {
    echo "ERROR: $*" >&2
    exit 1
}

store_is_git() {
    [[ -d "${PASSWORD_STORE_DIR:-${HOME}/.password-store}/.git" ]]
}

read_manifest() {
    pass show "${MANIFEST}" 2>/dev/null ||
        die "no '${MANIFEST}' entry in password-store (expected 'entry:relative/path' per line)"
}

save_entry() {
    local name="$1" file="${ROOT}/$2"
    if [[ ! -f "${file}" ]]; then
        echo "  skip   $2 (missing)"
        return
    fi
    pass insert -m "${name}" <"${file}" >/dev/null
    echo "  saved  $2"
}

load_entry() {
    local name="$1" file="${ROOT}/$2" tmp
    if ! pass show "${name}" >/dev/null 2>&1; then
        echo "  skip   $2 (not in store)"
        return
    fi

    tmp="$(mktemp)"
    trap 'rm -f "${tmp}"' RETURN

    pass show "${name}" >"${tmp}"
    if [[ -f "${file}" ]] && ! cmp -s "${tmp}" "${file}"; then
        cp "${file}" "${file}.bak"
    fi
    mkdir -p "$(dirname "${file}")"
    cp "${tmp}" "${file}"
    echo "  loaded $2"
}

for_each_entry() {
    local action="$1" line name path
    while IFS= read -r line; do
        if [[ -z "${line}" || "${line}" == \#* ]]; then
            continue
        fi
        name="${line%%:*}"
        path="${line#*:}"
        "${action}" "${name}" "${path}"
    done < <(read_manifest)
}

save_all() {
    echo "Saving local files into password-store:"
    for_each_entry save_entry

    if store_is_git; then
        echo "Pushing password-store:"
        pass git push
    fi
}

load_all() {
    if store_is_git; then
        echo "Pulling password-store:"
        pass git pull --ff-only
    fi

    echo "Loading password-store into local files:"
    for_each_entry load_entry
}

main() {
    command -v pass >/dev/null || die "pass is not installed"

    case "${1:-}" in
    save) save_all ;;
    load) load_all ;;
    *) die "usage: secrets.sh {save|load}" ;;
    esac
}

main "$@"
