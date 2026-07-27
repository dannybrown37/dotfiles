#!/usr/bin/env bash

set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"

# The list of what to sync lives inside the store, not in this repo.
readonly MANIFEST="manifest"

readonly QUEUE_SCRIPT="scripts/queue.py"

# Files a straight copy would corrupt: each machine edits its own copy, so both
# sides have to survive a sync. Order matters -- the queue merge asks
# .queue-complete which titles are already done, so that has to reconcile first.
readonly MERGE_PATHS=(".queue-complete" ".queue")

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

is_merge_path() {
    local path="$1" candidate
    for candidate in "${MERGE_PATHS[@]}"; do
        if [[ "${candidate}" == "${path}" ]]; then
            return 0
        fi
    done
    return 1
}

# Reconcile the local file with the store's copy in place, so both directions
# of the sync end up with the union instead of the last writer's snapshot.
# "prefer" decides only who wins on items both sides already have; keeping it
# tied to the direction is what stops the two machines rewriting each other's
# ordering forever.
merge_local_file() {
    local path="$1" incoming="$2" prefer="$3"

    command -v python3 >/dev/null ||
        die "python3 is required to merge ${path}"

    case "${path}" in
    .queue-complete)
        python3 "${ROOT}/${QUEUE_SCRIPT}" merge-completed \
            --complete-path "${ROOT}/${path}" \
            --incoming "${incoming}"
        ;;
    .queue)
        python3 "${ROOT}/${QUEUE_SCRIPT}" merge-queue \
            --queue-path "${ROOT}/${path}" \
            --complete-path "${ROOT}/.queue-complete" \
            --incoming "${incoming}" \
            --prefer "${prefer}"
        ;;
    *)
        die "no merge handler for ${path}"
        ;;
    esac
}

save_entry() {
    local name="$1" path="$2" file="${ROOT}/$2"
    if [[ ! -f "${file}" ]]; then
        echo "  skip   $2 (missing)"
        return
    fi

    if is_merge_path "${path}"; then
        # Overwriting here would drop whatever the other machine pushed since
        # this one last loaded.
        if ! pass show "${name}" >"${WORK_DIR}/incoming" 2>/dev/null; then
            : >"${WORK_DIR}/incoming"
        fi
        merge_local_file "${path}" "${WORK_DIR}/incoming" local
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
    local name="$1" path="$2" file="${ROOT}/$2" tmp
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

    if is_merge_path "${path}"; then
        merge_local_file "${path}" "${tmp}" incoming
    else
        cp "${tmp}" "${file}"
        echo "  loaded $2"
    fi
}

order_entries() {
    local -n source_lines="$1"
    local wanted line
    local -a merge_lines=() plain_lines=()

    for wanted in "${MERGE_PATHS[@]}"; do
        for line in ${source_lines[@]+"${source_lines[@]}"}; do
            if [[ "${line#*:}" == "${wanted}" ]]; then
                merge_lines+=("${line}")
            fi
        done
    done

    for line in ${source_lines[@]+"${source_lines[@]}"}; do
        if ! is_merge_path "${line#*:}"; then
            plain_lines+=("${line}")
        fi
    done

    printf '%s\n' ${merge_lines[@]+"${merge_lines[@]}"} \
        ${plain_lines[@]+"${plain_lines[@]}"}
}

for_each_entry() {
    local action="$1" manifest_text line name path
    local -a entries=()

    # Read up front: inside a process substitution, a failure here would only
    # kill the subshell and leave the caller reporting a successful no-op.
    manifest_text="$(read_manifest)"

    while IFS= read -r line; do
        if [[ -z "${line}" || "${line}" == \#* ]]; then
            continue
        fi
        entries+=("${line}")
    done <<<"${manifest_text}"

    while IFS= read -r line; do
        if [[ -z "${line}" ]]; then
            continue
        fi
        name="${line%%:*}"
        path="${line#*:}"
        "${action}" "${name}" "${path}"
    done < <(order_entries entries)
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
