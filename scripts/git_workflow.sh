#!/usr/bin/env bash
# @doc Backs the git start/ship/fix/rescue/done/purge aliases in config/.gitconfig | git_workflow.sh help

set -euo pipefail

readonly EXIT_USAGE=2
readonly VERSION="1.10.0"

usage() {
    cat <<'EOF'
Usage: git <command> [args...]

  git start <topic>    Go to the base branch, pull, make branch <topic> (carries uncommitted changes)
                       On the base with local commits: move them to <topic>
  git start -s <topic> Stack: make branch <topic> on top of the current branch
  git ship [--no-auto] [--no-done]
                       Push, open a PR, turn on auto-merge, watch CI, then git done
                       No auto-merge: skip the CI watch, merge by hand after CI
                       --no-auto: leave auto-merge off
                       Repo without auto-merge: PR body uses the work template
                       Stacked: the PR targets the parent branch, no auto-merge,
                       lower branches that moved are force-pushed (with lease),
                       and the PRs are linked into a GitHub stack (gh-stack extension)
  git fix              Fold staged changes into the commits they fix, anywhere in
                       the stack (git-absorb), then push every branch that moved
  git done             After the merge: go back to the base branch and pull (carries uncommitted changes)
                       Stacked: once the parent merges or moves, rebase onto it and stay
  git rescue <topic>   Move commits made after a PR merged onto a new branch <topic>
  git purge [--all] [-y]
                       Delete local branches whose origin branch is gone (merged PRs)
                       --all: every branch but the base, main/master/develop, and worktrees; asks first
                       -y: with --all, don't ask

The base branch is origin's default branch (main, master, develop, ...).
See docs/git-workflow.md.
EOF
}

base_branch() {
    local head
    head="$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD)" ||
        { git remote set-head origin --auto >/dev/null &&
            head="$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD)"; } ||
        fail 1 "can't find origin's default branch: run git remote set-head origin <branch>"
    echo "${head#origin/}"
}

fail() {
    local code="$1"
    shift
    echo "$*" >&2
    exit "${code}"
}

# gh ignores git's per-remote credential helpers, so without this it acts as
# whichever account gh/GITHUB_TOKEN holds -- not the one git pushes as.
use_push_token_for_gh() {
    local url token
    url="$(git config --get remote.origin.url)" || return 0
    [[ "${url}" == https://github.com/* ]] || return 0
    token="$(printf 'url=%s\n\n' "${url}" |
        GIT_TERMINAL_PROMPT=0 git credential fill 2>/dev/null |
        sed -n 's/^password=//p')" || return 0
    [[ -n "${token}" ]] && export GH_TOKEN="${token}"
    return 0
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

# gh's watch table cuts links to fit the pane, which breaks them. gh's
# hyperlink emits escape codes even when piped, so full URLs off a terminal.
print_check_links() {
    if [[ -t 1 ]]; then
        gh pr checks --json name,link \
            --template '{{range .}}{{hyperlink .link .name}}{{"\n"}}{{end}}' || true
    else
        gh pr checks --json name,link -q '.[] | .name + "\n" + .link' || true
    fi
}

merged_head() {
    local pr polls=0
    while [[ "${polls}" -lt 30 ]]; do
        pr="$(gh pr view --json state,headRefOid -q '.state + " " + .headRefOid' 2>/dev/null || true)"
        if [[ "${pr%% *}" == MERGED ]]; then
            echo "${pr#* }"
            return
        fi
        polls=$((polls + 1))
        sleep "${GIT_SHIP_POLL_SECS:-2}"
    done
    return 1
}

done_after_merge() {
    local merged
    if ! merged="$(merged_head)"; then
        echo 'CI green but PR not merged after 60s: run git done once it merges' >&2
    elif [[ "${merged}" != "$(git rev-parse HEAD)" ]]; then
        echo 'PR merged without your newest commits: run git rescue <topic>' >&2
    else
        cmd_done
    fi
}

pop_carried() {
    git stash pop --index 2>/dev/null && return
    echo 'staged changes did not apply to the new base: carrying them unstaged' >&2
    git stash pop
}

with_carried_changes() {
    local label="$1" from stashed=0
    shift
    from="$(git branch --show-current)"
    if [[ -n "$(git status --porcelain)" ]]; then
        git stash push -u -m "${label}"
        stashed=1
    fi
    if ! "$@"; then
        if [[ "${stashed}" == 1 ]]; then
            git switch "${from}" >/dev/null 2>&1 || true
            pop_carried
        fi
        exit 1
    fi
    if [[ "${stashed}" == 1 ]] && ! pop_carried; then
        fail 1 'carried changes conflict: fix the files, git add them, then git stash drop'
    fi
}

cmd_start() {
    local arg topic='' stack=0 usage='usage: git start [-s] <topic>'
    for arg in "$@"; do
        case "${arg}" in
        -s | --stack) stack=1 ;;
        -*) fail "${EXIT_USAGE}" "${usage}" ;;
        *)
            [[ -z "${topic}" ]] || fail "${EXIT_USAGE}" "${usage}"
            topic="${arg}"
            ;;
        esac
    done
    [[ -n "${topic}" ]] || fail "${EXIT_USAGE}" "${usage}"
    if [[ "${stack}" == 1 ]]; then
        stack_on_current "${topic}"
        return
    fi
    git fetch origin "${BASE}"
    if [[ "$(git branch --show-current)" == "${BASE}" ]] && base_has_own_commits; then
        move_base_commits "${topic}"
    else
        with_carried_changes "git start ${topic}" branch_from_base "${topic}"
    fi
}

base_has_own_commits() {
    ! git merge-base --is-ancestor "${BASE}" "origin/${BASE}" &&
        ! git diff --quiet "${BASE}" "origin/${BASE}"
}

# Commits made on the base by mistake: the topic keeps them, the base goes
# back to origin. The base moves first, so a conflict leaves only the rebase.
move_base_commits() {
    local topic="$1" remote="origin/${BASE}" stashed=0
    git switch -c "${topic}"
    git branch -f "${BASE}" "${remote}"
    # Not --autostash: it drops what was staged.
    if [[ -n "$(git status --porcelain)" ]]; then
        git stash push -u -m "git start ${topic}"
        stashed=1
    fi
    if ! git rebase "${remote}"; then
        [[ "${stashed}" == 0 ]] || fail 1 'fix the conflicts, git rebase --continue, then git stash pop --index'
        fail 1 'fix the conflicts, git rebase --continue'
    fi
    if [[ "${stashed}" == 1 ]] && ! pop_carried; then
        fail 1 'carried changes conflict: fix the files, git add them, then git stash drop'
    fi
    echo "moved commits made on ${BASE} to ${topic}" >&2
}

stack_on_current() {
    local topic="$1" parent
    parent="$(git branch --show-current)"
    [[ -n "${parent}" && "${parent}" != "${BASE}" ]] ||
        fail "${EXIT_USAGE}" "on ${parent:-detached HEAD}: nothing to stack on, use git start ${topic}"
    git switch -c "${topic}"
    git config "branch.${topic}.stackParent" "${parent}"
    git config "branch.${topic}.stackBase" "$(git rev-parse HEAD)"
}

stack_parent() {
    git config --get "branch.$1.stackParent" || true
}

# The newest commit the branch shares with its parent. The parent tip is exact
# while the branch sits on it; once the parent is rewritten (squash-merged or
# restacked) only the recorded stackBase still marks the fork.
stack_fork() {
    local branch="$1" parent="$2" base
    if git merge-base --is-ancestor "${parent}" HEAD 2>/dev/null; then
        echo "${parent}"
    elif base="$(git config --get "branch.${branch}.stackBase")" &&
        git merge-base --is-ancestor "${base}" HEAD; then
        echo "${base}"
    else
        fail 1 "can't find where ${branch} forks from ${parent}"
    fi
}

# Prints the stack bottom-to-top, ending at $1. A branch made without
# git start -s has no stackParent, so its open PR's base stands in, and is
# recorded so git done can restack it later.
stack_chain() {
    local branch="$1" parent pr depth=0 chain=()
    while [[ -n "${branch}" && "${branch}" != "${BASE}" && "${depth}" -lt 20 ]]; do
        chain=("${branch}" "${chain[@]}")
        depth=$((depth + 1))
        parent="$(stack_parent "${branch}")"
        if [[ -z "${parent}" ]]; then
            pr="$(gh pr view "${branch}" --json state,baseRefName \
                -q '.state + " " + .baseRefName' 2>/dev/null || true)"
            [[ "${pr%% *}" == OPEN ]] || break
            parent="${pr#* }"
            if [[ "${parent}" != "${BASE}" ]] &&
                git rev-parse --verify --quiet "refs/heads/${parent}" >/dev/null; then
                git config "branch.${branch}.stackParent" "${parent}"
                git config "branch.${branch}.stackBase" "$(git merge-base "${parent}" "${branch}")"
            fi
        fi
        branch="${parent}"
    done
    printf '%s\n' "${chain[@]}"
}

on_origin() {
    git rev-parse --verify --quiet "refs/heads/$1" >/dev/null &&
        git rev-parse --verify --quiet "refs/remotes/origin/$1" >/dev/null
}

# Bottom-up, so a PR never shows a parent's stale commits. Checks every
# branch before pushing any; the lease stops a push the last fetch missed.
push_stack() {
    local b
    for b in "$@"; do
        on_origin "${b}" || continue
        if [[ "$(git rev-parse "${b}")" != "$(git rev-parse "origin/${b}")" ]] &&
            git merge-base --is-ancestor "${b}" "origin/${b}"; then
            fail 1 "${b} is behind origin/${b}: git switch ${b} && git pull"
        fi
    done
    for b in "$@"; do
        on_origin "${b}" || continue
        [[ "$(git rev-parse "${b}")" != "$(git rev-parse "origin/${b}")" ]] || continue
        git push --force-with-lease origin "${b}"
    done
}

# GitHub only shows a stack once its PRs are linked; a parent-based PR alone
# isn't one. Never fails the ship: stacks are a preview feature.
link_stack() {
    local out
    if out="$(gh stack link --base "${BASE}" --remote origin "$@" 2>&1 </dev/null)"; then
        [[ -z "${out}" ]] || echo "${out}" >&2
        return
    fi
    if [[ "${out}" == *'unknown command "stack"'* ]]; then
        echo 'GitHub stack not linked: gh extension install github/gh-stack, then git ship again' >&2
    else
        echo "GitHub stack not linked: ${out}" >&2
    fi
}

require_open_parent() {
    local parent="$1" state
    git ls-remote --exit-code --heads origin "${parent}" >/dev/null ||
        fail "${EXIT_USAGE}" "${parent} is not on origin: git ship it first"
    state="$(gh pr view "${parent}" --json state -q .state 2>/dev/null || true)"
    [[ "${state}" != MERGED ]] || fail "${EXIT_USAGE}" "${parent} already merged: run git done first"
}

repo_allows_auto_merge() {
    [[ "$(gh api 'repos/{owner}/{repo}' -q .allow_auto_merge 2>/dev/null)" != false ]]
}

pr_body() {
    local since="$1" commits
    commits="$(git log --reverse --format='- %s' "${since}..HEAD")"
    if repo_allows_auto_merge; then
        echo "${commits}"
        return
    fi
    printf '%s\n\n%s\n\n%s\n\n%s\n' \
        '## Why These Changes and What They Are' "${commits}" \
        '## Evidence of Testing' '## QA Testing Instructions'
}

cmd_ship() {
    local arg branch parent since prefix state auto=1 run_done=1 ci=0 chain
    for arg in "$@"; do
        case "${arg}" in
        --no-auto) auto=0 ;;
        --no-done) run_done=0 ;;
        *) fail "${EXIT_USAGE}" 'usage: git ship [--no-auto] [--no-done]' ;;
        esac
    done
    branch="$(git branch --show-current)"
    [[ "${branch}" != "${BASE}" ]] || fail "${EXIT_USAGE}" "on ${BASE}: run git start <topic> first"
    parent="$(stack_parent "${branch}")"
    since="origin/${BASE}"
    if [[ -n "${parent}" ]]; then
        since="$(stack_fork "${branch}" "${parent}")"
    fi
    prefix="$(git log --format=%s "${since}..HEAD" | top_prefix)"
    [[ -n "${prefix}" ]] || fail "${EXIT_USAGE}" "no conventional commit prefix in ${since}..HEAD"
    [[ -z "${parent}" ]] || require_open_parent "${parent}"
    state="$(gh pr view --json state -q .state 2>/dev/null || true)"
    [[ "${state}" != MERGED ]] ||
        fail "${EXIT_USAGE}" "PR for ${branch} already merged: run git done, or git rescue <topic> to keep new commits"
    chain=("${branch}")
    [[ -z "${parent}" ]] || mapfile -t chain < <(stack_chain "${branch}")
    push_stack "${chain[@]}"
    git push --force-with-lease -u origin HEAD
    if [[ "${state}" != OPEN ]]; then
        gh pr create \
            --base "${parent:-${BASE}}" \
            --title "${prefix}: $(tr '_-' '  ' <<<"${branch}")" \
            --body "$(pr_body "${since}")"
    fi
    if [[ -n "${parent}" ]]; then
        link_stack "${chain[@]}"
        echo "stacked PR: once ${parent} merges, run git done here" >&2
        return
    fi
    if [[ "${auto}" == 0 ]] || ! gh pr merge --auto --squash --delete-branch; then
        echo 'auto-merge is off: after CI: gh pr merge --squash --delete-branch' >&2
        return
    fi
    wait_for_checks
    gh pr checks --watch || ci=$?
    print_check_links
    [[ "${ci}" == 0 ]] || exit "${ci}"
    [[ "${run_done}" == 0 ]] || done_after_merge
}

# Folds staged changes into the commits they fix, anywhere in the stack, then
# pushes every branch that moved. Absorb's own --and-rebase opens an editor.
cmd_fix() {
    local branch fork before leftover chain
    [[ $# -eq 0 ]] || fail "${EXIT_USAGE}" 'usage: git fix (stage the fix first)'
    branch="$(git branch --show-current)"
    [[ -n "${branch}" && "${branch}" != "${BASE}" ]] ||
        fail "${EXIT_USAGE}" "on ${branch:-detached HEAD}: git fix works on a topic branch"
    ! git diff --cached --quiet || fail "${EXIT_USAGE}" 'nothing staged: git add the fix, then git fix'
    command -v git-absorb >/dev/null ||
        fail 1 'git fix needs git-absorb: https://github.com/tummychow/git-absorb#installing'
    git fetch origin "${BASE}"
    fork="$(git merge-base HEAD "origin/${BASE}")"
    before="$(git rev-parse HEAD)"
    git absorb --no-limit --base "${fork}"
    leftover="$(git diff --cached --name-only)"
    if [[ "$(git rev-parse HEAD)" != "${before}" ]]; then
        GIT_SEQUENCE_EDITOR=: git -c rebase.updateRefs=true \
            rebase --interactive --autosquash --autostash "${fork}" ||
            fail 1 'fix the conflicts, git rebase --continue, then git ship'
    fi
    [[ -z "${leftover}" ]] ||
        fail 1 "no commit to fold these into, nothing pushed: commit them, then git ship"$'\n'"${leftover}"
    mapfile -t chain < <(stack_chain "${branch}")
    push_stack "${chain[@]}"
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
    git fetch origin "${BASE}"
    git switch -c "${topic}"
    git rebase --onto "origin/${BASE}" "${merged_head}"
}

# Moves the base ref before any checkout, so the working tree never holds a
# stale base (file watchers like ahk/main.ahk reload on every change).
update_base() {
    local remote="origin/${BASE}"
    if ! git rev-parse --verify --quiet "${BASE}" >/dev/null; then
        git branch --track "${BASE}" "${remote}" >/dev/null
    elif ! git merge-base --is-ancestor "${BASE}" "${remote}"; then
        if ! git diff --quiet "${BASE}" "${remote}"; then
            echo "local ${BASE} has commits not on ${remote}: git switch -c <topic> ${BASE} to keep them, then git branch -f ${BASE} ${remote}" >&2
            return 1
        fi
        echo "local ${BASE} matches ${remote} (already squash-merged): resetting to it" >&2
    fi
    if [[ "$(git branch --show-current)" == "${BASE}" ]]; then
        git reset --keep "${remote}"
    else
        git branch -f "${BASE}" "${remote}"
    fi
}

sync_base() {
    git fetch origin "${BASE}" && update_base && git switch "${BASE}"
}

branch_from_base() {
    update_base && git switch -c "$1" "${BASE}"
}

# Config moves before the rebase, so a conflict leaves nothing to redo:
# finish the rebase and push.
restack() {
    local branch="$1" parent="$2" fork onto
    fork="$(stack_fork "${branch}" "${parent}")"
    if [[ "$(gh pr view "${parent}" --json state -q .state 2>/dev/null || true)" == MERGED ]]; then
        git fetch origin "${BASE}"
        onto="origin/${BASE}"
        git config --unset "branch.${branch}.stackParent"
        git config --unset "branch.${branch}.stackBase"
        if [[ "$(gh pr view --json state -q .state 2>/dev/null || true)" == OPEN ]]; then
            gh pr edit --base "${BASE}"
        fi
    elif [[ "${fork}" == "${parent}" ]]; then
        echo "${parent} not merged yet: nothing to do" >&2
        return
    else
        onto="${parent}"
        git config "branch.${branch}.stackBase" "$(git rev-parse "${parent}")"
    fi
    git rebase --autostash --onto "${onto}" "${fork}" ||
        fail 1 'fix the conflicts, git rebase --continue, then git push --force-with-lease'
    if git rev-parse --verify --quiet "refs/remotes/origin/${branch}" >/dev/null; then
        git push --force-with-lease origin HEAD
    fi
}

cmd_done() {
    local branch parent dirty
    branch="$(git branch --show-current)"
    parent="$(stack_parent "${branch}")"
    if [[ -n "${parent}" ]]; then
        restack "${branch}" "${parent}"
        return
    fi
    dirty="$(git status --porcelain)"
    with_carried_changes 'git done' sync_base
    [[ -z "${dirty}" ]] || echo "carried uncommitted changes to ${BASE}: git start <topic> to keep working" >&2
}

purgeable() {
    local all="$1" branch track worktree
    while IFS='|' read -r branch track worktree; do
        case "${branch}" in
        "${BASE}" | main | master | develop) continue ;;
        esac
        [[ -z "${worktree}" ]] || continue
        [[ "${all}" == 1 || "${track}" == '[gone]' ]] && echo "${branch}"
    done < <(git for-each-ref --format='%(refname:short)|%(upstream:track)|%(worktreepath)' refs/heads)
    return 0
}

cmd_purge() {
    local arg all=0 yes=0 answer branches
    for arg in "$@"; do
        case "${arg}" in
        --all) all=1 ;;
        -y | --yes) yes=1 ;;
        *) fail "${EXIT_USAGE}" 'usage: git purge [--all] [-y]' ;;
        esac
    done
    git fetch --prune --quiet origin
    branches="$(purgeable "${all}")"
    if [[ -z "${branches}" ]]; then
        echo 'nothing to purge' >&2
        return
    fi
    if [[ "${all}" == 1 && "${yes}" == 0 ]]; then
        echo "${branches}" >&2
        read -r -p "delete $(wc -l <<<"${branches}") branches, merged or not? [y/N] " answer || true
        [[ "${answer}" == [yY] ]] || fail 1 'nothing deleted'
    fi
    xargs git branch -D <<<"${branches}"
}

main() {
    if [[ $# -eq 0 ]]; then
        usage >&2
        exit "${EXIT_USAGE}"
    fi

    local cmd="$1"
    shift
    case "${cmd}" in
    purge) BASE="$(base_branch)" ;;
    start | ship | fix | rescue | done)
        BASE="$(base_branch)"
        use_push_token_for_gh
        ;;
    esac
    case "${cmd}" in
    -h | --help | help) usage ;;
    -v | --version) echo "git_workflow ${VERSION}" ;;
    start) cmd_start "$@" ;;
    ship) cmd_ship "$@" ;;
    fix) cmd_fix "$@" ;;
    rescue) cmd_rescue "$@" ;;
    done) cmd_done "$@" ;;
    purge) cmd_purge "$@" ;;
    *)
        echo "unknown command: ${cmd}" >&2
        usage >&2
        exit "${EXIT_USAGE}"
        ;;
    esac
}

main "$@"
