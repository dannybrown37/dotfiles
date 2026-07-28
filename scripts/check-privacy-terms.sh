#!/usr/bin/env bash
# Blocks a commit when a newly added line matches a term from PRIVACY_TERMS,
# a user-controlled array defined in the gitignored config/.secrets.

set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
SECRETS_FILE="${ROOT}/config/.secrets"

PRIVACY_TERMS=()
if [[ -f "${SECRETS_FILE}" ]]; then
    # config/.secrets ends in a bare `[[ ... ]] && cmd` whose false branch
    # would otherwise trip set -e here.
    set +e
    # shellcheck disable=SC1090
    source "${SECRETS_FILE}"
    set -e
fi

if [[ ${#PRIVACY_TERMS[@]} -eq 0 ]]; then
    exit 0
fi

found=0

while IFS= read -r -d '' file; do
    while IFS= read -r line; do
        [[ "${line}" == +++* ]] && continue
        [[ "${line}" == +* ]] || continue
        content="${line#+}"
        for term in "${PRIVACY_TERMS[@]}"; do
            if grep -qiF -- "${term}" <<<"${content}"; then
                echo "BLOCKED: ${file} contains privacy term '${term}':" >&2
                echo "  ${content}" >&2
                found=1
            fi
        done
    done < <(git diff --cached -U0 -- "${file}")
done < <(git diff --cached --name-only --diff-filter=ACM -z)

if [[ "${found}" -eq 1 ]]; then
    echo "Remove the flagged content, or update PRIVACY_TERMS in config/.secrets, before committing." >&2
    exit 1
fi

exit 0
