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

readonly bootstrap_paths='^(install/|config/|justfile$|scripts/just-help\.sh$|\.github/workflows/ci\.yml$)'

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

if grep -qE "${bootstrap_paths}" <<<"${changed}"; then
    echo true
else
    echo false
fi
