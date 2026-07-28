#!/usr/bin/env bash

set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"

# The list of what to sync lives inside the store, not in this repo.
readonly MANIFEST="manifest"

# queue_cli.py lives in the skill-tree repo, not here -- same @anchor-style
# resolution the queue CLI itself uses, just not manifest-driven since this is
# an internal implementation detail rather than a synced file.
readonly QUEUE_SCRIPT="${SKILL_TREE_DIR:-${PROJECTS_DIR:-${HOME}/projects}/skill-tree}/skills/queue/scripts/queue_cli.py"

# Files a straight copy would corrupt: each machine edits its own copy, so both
# sides have to survive a sync. Order matters -- the queue merge asks
# queue-complete which titles are already done, so that has to reconcile first.
readonly MERGE_PATHS=("queue-complete" "queue")

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
        if [[ "${candidate}" == "${path##*/}" ]]; then
            return 0
        fi
    done
    return 1
}

# Manifest paths are relative to this repo unless they start with an @anchor,
# which names another repo that may or may not be cloned on this machine, or
# with ~/, which resolves under $HOME regardless of this repo -- for entries
# that don't belong to any one repo (e.g. the shared queue).
anchor_of() {
    local path="$1"
    [[ "${path}" == @* ]] || return 1
    printf '%s\n' "${path%%/*}" | cut -c2-
}

is_home_path() {
    # Matching the manifest's literal "~/" text, not expanding a real path.
    # shellcheck disable=SC2088
    [[ "$1" == '~/'* ]]
}

resolve_anchor() {
    local anchor="$1" home_var base
    home_var="$(printf '%s' "${anchor}" | tr '[:lower:]-' '[:upper:]_')_HOME"
    base="${!home_var:-${PROJECTS_DIR:-${HOME}/projects}/${anchor}}"

    [[ -d "${base}" ]] || return 1
    printf '%s\n' "${base}"
}

# Checked while reading the manifest: `die` inside the command substitution
# that resolve_entry_file runs in would only kill the subshell.
validate_entry_path() {
    local path="$1"
    if [[ "${path}" == @* && "${path}" != */* ]]; then
        die "malformed anchor '${path}': expected @<repo>/<relative-path>"
    fi
    # shellcheck disable=SC2088
    if [[ "${path}" == '~'* && ("${path}" != '~/'* || "${path}" == '~/') ]]; then
        die "malformed home path '${path}': expected ~/<relative-path>"
    fi
}

# Prints the absolute file path, or nothing when the anchored repo is not
# cloned on this machine.
resolve_entry_file() {
    local path="$1" anchor base

    if is_home_path "${path}"; then
        printf '%s\n' "${HOME}/${path#\~/}"
        return 0
    fi

    if ! anchor="$(anchor_of "${path}")"; then
        printf '%s\n' "${ROOT}/${path}"
        return 0
    fi

    if base="$(resolve_anchor "${anchor}")"; then
        printf '%s\n' "${base}/${path#*/}"
    fi
}

# Reconcile the local file with the store's copy in place, so both directions
# of the sync end up with the union instead of the last writer's snapshot.
# "prefer" decides only who wins on items both sides already have; keeping it
# tied to the direction is what stops the two machines rewriting each other's
# ordering forever.
merge_local_file() {
    local file="$1" incoming="$2" prefer="$3"
    local kind="${file##*/}" dir="${file%/*}"

    command -v python3 >/dev/null ||
        die "python3 is required to merge ${kind}"
    [[ -f "${QUEUE_SCRIPT}" ]] ||
        die "queue_cli.py not found at ${QUEUE_SCRIPT} -- is skill-tree cloned? (see \$SKILL_TREE_DIR)"

    case "${kind}" in
    queue-complete)
        python3 "${QUEUE_SCRIPT}" merge-completed \
            --complete-path "${file}" \
            --incoming "${incoming}"
        ;;
    queue)
        python3 "${QUEUE_SCRIPT}" merge-queue \
            --queue-path "${file}" \
            --complete-path "${dir}/queue-complete" \
            --incoming "${incoming}" \
            --prefer "${prefer}"
        ;;
    *)
        die "no merge handler for ${kind}"
        ;;
    esac
}

save_entry() {
    local name="$1" path="$2" file
    file="$(resolve_entry_file "${path}")"

    if [[ -z "${file}" ]]; then
        echo "  skip   $2 ($(anchor_of "${path}") not installed)"
        return
    fi

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
        merge_local_file "${file}" "${WORK_DIR}/incoming" local
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
    local name="$1" path="$2" file tmp
    file="$(resolve_entry_file "${path}")"

    if [[ -z "${file}" ]]; then
        echo "  skip   $2 ($(anchor_of "${path}") not installed)"
        return
    fi

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
        merge_local_file "${file}" "${tmp}" incoming
    else
        cp "${tmp}" "${file}"
        echo "  loaded $2"
    fi
}

order_entries() {
    local -n source_lines="$1"
    local wanted line path
    local -a merge_lines=() plain_lines=()

    for wanted in "${MERGE_PATHS[@]}"; do
        for line in ${source_lines[@]+"${source_lines[@]}"}; do
            path="${line#*:}"
            if [[ "${path##*/}" == "${wanted}" ]]; then
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
        validate_entry_path "${line#*:}"
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

# Every `pass insert` commits, so two machines that each saved have diverged
# by construction -- the common case, not an error. --ff-only refused all of
# them; rebase replays the local commits and only stops when the same entry
# changed on both sides. --autostash covers a half-finished earlier run.
sync_pull() {
    store_is_git || return 0

    echo "Pulling password-store:"
    if pass git pull --rebase --autostash; then
        return 0
    fi

    # Left mid-rebase, every later `pass insert` would commit onto a detached
    # HEAD and vanish at the next checkout.
    pass git rebase --abort 2>/dev/null || true
    die "password-store pull conflicted -- same entry changed on both machines.
  Resolve by hand, keeping one side (encrypted blobs cannot merge):
    pass git pull --rebase
    pass git checkout --ours <entry>.gpg    # or --theirs
    pass git add <entry>.gpg && pass git rebase --continue"
}

save_all() {
    # Saving merges .queue against the store, so pull first or the merge runs
    # against a stale copy and the push is rejected anyway.
    sync_pull

    echo "Saving local files into password-store:"
    for_each_entry save_entry

    if store_is_git; then
        echo "Pushing password-store:"
        pass git push
    fi
}

load_all() {
    sync_pull

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
