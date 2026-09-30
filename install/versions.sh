#!/usr/bin/env bash
# shellcheck disable=SC2034

##
## Single source of truth for pinned tool versions.
## Sourced by install/extras/python.sh (to install) and scripts/dotfiles_audit.sh (to
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
## Renovate bumps every pin that carries a `# renovate:` line (see renovate.json).
## TOKEI stays at v12, the last release with binaries, and the AHK SHA is a
## commit -- both are bumped by hand.
##

# renovate: datasource=pypi depName=ruff
RUFF_VERSION=0.16.0
# renovate: datasource=pypi depName=prek
PREK_VERSION=0.4.14
# renovate: datasource=github-releases depName=casey/just
JUST_VERSION=1.58.0
# renovate: datasource=github-releases depName=eza-community/eza
EZA_VERSION=0.23.5
# renovate: datasource=github-releases depName=tummychow/git-absorb
GIT_ABSORB_VERSION=0.9.0
# renovate: datasource=github-releases depName=ajeetdsouza/zoxide
ZOXIDE_VERSION=0.10.0
# renovate: datasource=github-releases depName=equalsraf/win32yank
WIN32YANK_VERSION=0.1.1
TOKEI_VERSION=12.1.2
# renovate: datasource=github-releases depName=sharkdp/hyperfine
HYPERFINE_VERSION=1.20.0
# renovate: datasource=github-releases depName=charmbracelet/glow
GLOW_VERSION=3.0.0
# renovate: datasource=github-releases depName=fastfetch-cli/fastfetch
FASTFETCH_VERSION=2.69.0
# renovate: datasource=github-releases depName=dandavison/delta
DELTA_VERSION=0.19.2
# renovate: datasource=github-releases depName=Wilfred/difftastic
DIFFTASTIC_VERSION=0.71.0
# renovate: datasource=github-releases depName=mgdm/htmlq
HTMLQ_VERSION=0.4.0
# renovate: datasource=github-releases depName=PaulJuliusMartinez/jless
JLESS_VERSION=0.9.0
# renovate: datasource=github-releases depName=junegunn/fzf
FZF_VERSION=0.74.4
# renovate: datasource=github-releases depName=neovim/neovim
NVIM_VERSION=0.12.5
# GOLANG, not GO: CI exports these, and GO_VERSION is a name Go tooling claims.
# renovate: datasource=golang-version depName=go
GOLANG_VERSION=1.27.1
# renovate: datasource=github-releases depName=tj/n
N_VERSION=10.2.0
# renovate: datasource=github-releases depName=astral-sh/uv
UV_VERSION=0.12.20
AHK_AUTOCORRECT_SHA=3a174b6182a246a648f82da02735702b8714ff24
