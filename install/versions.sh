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
## silently -- that is how prek ended up pinned here and floating in CI.
##
## Bump by hand. prek-autoupdate.yml bumps hook revs, not these, and
## dependabot cannot see them either.
##

RUFF_VERSION=0.16.0
PREK_VERSION=0.4.14
JUST_VERSION=1.58.0
