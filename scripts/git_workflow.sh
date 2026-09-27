#!/usr/bin/env bash
# @doc Backs the git start/ship/rescue/done aliases in config/.gitconfig | git_workflow.sh help

set -euo pipefail

readonly EXIT_USAGE=2
readonly VERSION="1.0.0"

usage() {
    cat <<'EOF'
Usage: git <command> [args...]

  git start <topic>    Go to main, pull, make branch <topic> (carries uncommitted changes)
  git ship             Push, open a PR, turn on auto-merge, watch CI
  git done             After the merge: go back to main and pull
  git rescue <topic>   Move commits made after a PR merged onto a new branch <topic>

See docs/git-workflow.md.
EOF
}

fail() {
    local code="$1"
    shift
    echo "$*" >&2
    exit "${code}"
}

top_prefix() {
    awk '
        BEGIN {
            n = split("chore style test docs ci build revert refactor perf fix feat", order, " ")
            for (i = 1; i <= n; i++) rank[order[i]] = i
        }
        match($0, /^[a-z]+(\([^)]*\))?!?:/) {
            kind = $0
            sub(/[(!:].*/, "", kind)
            if (rank[kind] > top) { top = rank[kind]; prefix = kind }
            if (substr($0, RLENGTH - 1, 1) == "!") bang = "!"
        }
        END { if (prefix) print prefix bang }
    '
}

no_checks_yet() {
    local out
    out="$(gh pr checks 2>&1 >/dev/null || true)"
    [[ "${out}" == *'no checks reported'* ]]
}

wait_for_checks() {
    local polls=0
    while no_checks_yet; do
        polls=$((polls + 1))
        [[ "${polls}" -lt 30 ]] || fail 1 'no CI checks after 60s: run gh pr checks --watch later'
        [[ "${polls}" != 1 ]] || echo 'waiting for CI to start...' >&2
        sleep "${GIT_SHIP_POLL_SECS:-2}"
    done
}

cmd_start() {
    local topic="${1:-}" from stashed=0
    [[ -n "${topic}" ]] || fail "${EXIT_USAGE}" 'usage: git start <topic>'
    from="$(git branch --show-current)"
    if [[ -n "$(git status --porcelain)" ]]; then
        git stash push -u -m "git start ${topic}"
        stashed=1
    fi
    if ! { git switch main && git pull --ff-only && git switch -c "${topic}"; }; then
        if [[ "${stashed}" == 1 ]]; then
            git switch "${from}" >/dev/null 2>&1 || true
            git stash pop
        fi
        exit 1
    fi
    if [[ "${stashed}" == 1 ]] && ! git stash pop; then
        fail 1 'carried changes conflict: fix the files, git add them, then git stash drop'
    fi
}

cmd_ship() {
    local branch prefix state
    branch="$(git branch --show-current)"
    [[ "${branch}" != main ]] || fail "${EXIT_USAGE}" 'on main: run git start <topic> first'
    prefix="$(git log --format=%s origin/main..HEAD | top_prefix)"
    [[ -n "${prefix}" ]] || fail "${EXIT_USAGE}" 'no conventional commit prefix in origin/main..HEAD'
    state="$(gh pr view --json state -q .state 2>/dev/null || true)"
    [[ "${state}" != MERGED ]] ||
        fail "${EXIT_USAGE}" "PR for ${branch} already merged: run git done, or git rescue <topic> to keep new commits"
    git push -u origin HEAD
    if [[ "${state}" != OPEN ]]; then
        gh pr create \
            --title "${prefix}: $(tr '_-' '  ' <<<"${branch}")" \
            --body "$(git log --reverse --format='- %s' origin/main..HEAD)"
    fi
    gh pr merge --auto --squash --delete-branch
    wait_for_checks
    gh pr checks --watch
}

cmd_rescue() {
    local topic="${1:-}" pr merged_head late
    [[ -n "${topic}" ]] || fail "${EXIT_USAGE}" 'usage: git rescue <topic>'
    [[ -z "$(git status --porcelain)" ]] || fail "${EXIT_USAGE}" 'uncommitted changes: commit or stash them first'
    pr="$(gh pr view --json state,headRefOid -q '.state + " " + .headRefOid' 2>/dev/null || true)"
    [[ "${pr%% *}" == MERGED ]] || fail "${EXIT_USAGE}" 'no merged PR for this branch: use git ship'
    merged_head="${pr#* }"
    late="$(git rev-list "${merged_head}..HEAD")"
    [[ -n "${late}" ]] || fail "${EXIT_USAGE}" 'nothing to rescue: run git done'
    git fetch origin main
    git switch -c "${topic}"
    git rebase --onto origin/main "${merged_head}"
}

cmd_done() {
    git switch main
    git fetch origin main
    if git merge-base --is-ancestor main origin/main; then
        git merge --ff-only origin/main
    elif git diff --quiet main origin/main; then
        echo 'local main matches origin/main (already squash-merged): resetting to it' >&2
        git reset --keep origin/main
    else
        fail 1 'local main has commits not on origin/main: git switch -c <topic> to keep them, then git branch -f main origin/main'
    fi
}

main() {
    if [[ $# -eq 0 ]]; then
        usage >&2
        exit "${EXIT_USAGE}"
    fi

    local cmd="$1"
    shift
    case "${cmd}" in
    -h | --help | help) usage ;;
    -v | --version) echo "git_workflow ${VERSION}" ;;
    start) cmd_start "$@" ;;
    ship) cmd_ship "$@" ;;
    rescue) cmd_rescue "$@" ;;
    done) cmd_done "$@" ;;
    *)
        echo "unknown command: ${cmd}" >&2
        usage >&2
        exit "${EXIT_USAGE}"
        ;;
    esac
}

main "$@"
