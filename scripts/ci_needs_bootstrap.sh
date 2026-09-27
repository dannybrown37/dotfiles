#!/usr/bin/env bash

set -euo pipefail

##
## Print `true` if the CI bootstrap job should run for <base>..<head>, else `false`.
##
## Usage: ci_needs_bootstrap.sh <base-sha> <head-sha>
##
## bootstrap is a required check, so ci.yml skips it with a job-level `if:`
## (a skipped job counts as passing) rather than a workflow `paths:` filter
## (the check would never report, and the PR would wait on it forever).
##

# Not the justfile or just-help.sh: lint's embed-command hook runs `just`, which
# parses the whole justfile and runs the help script on every PR. An edit to a
# `_ci` recipe slips past, but the weekly cold run catches it.
readonly bootstrap_paths='^(install/|\.github/workflows/ci\.yml$)'
# Bootstrap symlinks config/ files but never reads them, so only a file coming
# or going can break it -- an edit to one can't.
readonly config_paths='^config/'

base="${1:-}"
head="${2:?usage: ci_needs_bootstrap.sh <base-sha> <head-sha>}"

# New-branch pushes send an all-zeros base, and a force push can send one this
# clone never saw. With nothing to diff against, run it.
if [[ -z "${base}" || "${base}" =~ ^0+$ ]] || ! git cat-file -e "${base}^{commit}" 2>/dev/null; then
    echo true
    exit 0
fi

# Captured first: `git diff | grep -q` under pipefail turns grep's early exit
# into git's SIGPIPE, which reads as "no match" on a big enough diff.
# Three dots: diff from the merge base, so commits that landed on main after
# the PR branched don't count as the PR's changes.
changed="$(git diff --name-only "${base}...${head}")"
added_or_removed="$(git diff --name-only --no-renames --diff-filter=AD "${base}...${head}")"

if grep -qE "${bootstrap_paths}" <<<"${changed}" ||
    grep -qE "${config_paths}" <<<"${added_or_removed}"; then
    echo true
else
    echo false
fi
