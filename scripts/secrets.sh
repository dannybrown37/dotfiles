#!/usr/bin/env bash

set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"

# The list of what to sync lives inside the store, not in this repo.
readonly MANIFEST="manifest"

WORK_DIR="$(mktemp -d)"
readonly WORK_DIR
trap 'rm -rf "${WORK_DIR}"' EXIT

die() {
    echo "ERROR: $*" >&2
    exit 1
}

store_is_git() {
    [[ -d "${PASSWORD_STORE_DIR:-${HOME}/.password-store}/.git" ]]
}

read_manifest() {
    # Report gpg's own error -- a decrypt or agent failure is not the same
    # problem as a missing entry, and they need different fixes.
    if ! pass show "${MANIFEST}" 2>"${WORK_DIR}/manifest.err"; then
        die "cannot read '${MANIFEST}' from password-store: $(<"${WORK_DIR}/manifest.err")"
    fi
}

save_entry() {
    local name="$1" file="${ROOT}/$2"
    if [[ ! -f "${file}" ]]; then
        echo "  skip   $2 (missing)"
        return
    fi
    # Encryption is non-deterministic, so re-inserting unchanged content would
    # produce a new commit on every push.
    if pass show "${name}" 2>/dev/null | cmp -s - "${file}"; then
        echo "  same   $2"
        return
    fi
    pass insert -m -f "${name}" <"${file}" >/dev/null
    echo "  saved  $2"
}

load_entry() {
    local name="$1" file="${ROOT}/$2" tmp
    if ! pass show "${name}" >/dev/null 2>&1; then
        echo "  skip   $2 (not in store)"
        return
    fi

    tmp="${WORK_DIR}/entry"

    pass show "${name}" >"${tmp}"
    if [[ -f "${file}" ]] && ! cmp -s "${tmp}" "${file}"; then
        cp "${file}" "${file}.bak"
    fi
    mkdir -p "$(dirname "${file}")"
    cp "${tmp}" "${file}"
    echo "  loaded $2"
}

for_each_entry() {
    local action="$1" manifest_text line name path

    # Read up front: inside a process substitution, a failure here would only
    # kill the subshell and leave the caller reporting a successful no-op.
    manifest_text="$(read_manifest)"

    while IFS= read -r line; do
        if [[ -z "${line}" || "${line}" == \#* ]]; then
            continue
        fi
        name="${line%%:*}"
        path="${line#*:}"
        "${action}" "${name}" "${path}"
    done <<<"${manifest_text}"
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
