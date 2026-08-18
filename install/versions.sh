#!/usr/bin/env bash
# shellcheck disable=SC2034

##
## Single source of truth for pinned tool versions.
## Sourced by install/python.sh (to install) and scripts/dotfiles_audit.sh (to
## check); read by .github/workflows/ci.yml (to install the same versions in CI).
##
## Keep assignments unquoted and one-per-line in NAME=value form -- CI appends
## them straight to $GITHUB_ENV, which uses that exact format, so no parsing is
## needed on that side. A quoted value would carry its quotes into CI.
##
## Pin anything whose version can change what a command reports; leave the rest
## unpinned. An unpinned tool drifts local and CI onto different versions
## silently -- that is how pre-commit ended up 3.8.0 here and 4.x in CI.
##
## Bump by hand. pre-commit-autoupdate.yml bumps hook revs, not these, and
## dependabot cannot see them either.
##

RUFF_VERSION=0.16.0
PRE_COMMIT_VERSION=4.6.2
JUST_VERSION=1.58.0
