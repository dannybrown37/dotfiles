#!/usr/bin/env bash
## @just 16 Start Here | Clone the private password-store for secret sync

##
## Split out of the old install/bash.sh. Worth its own target because it is the
## only interactive part of the bootstrap -- it may prompt for `gh auth login` or
## a remote URL -- so burying it behind an `apt upgrade` and a dozen downloads
## meant a prompt appearing several minutes into an unattended run.
##
## Requires your GPG private key already imported; that transfer stays manual.
## See the Secrets section of README.md.
##

dotfiles="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ ! -d "${HOME}/.password-store" ]; then
    cloned=""

    if command -v gh &>/dev/null; then
        if ! gh auth status &>/dev/null; then
            read -rp "gh isn't logged in. Run 'gh auth login' now to clone password-store without handling a token by hand? [Y/n] " run_login
            if [[ "${run_login}" != "n" && "${run_login}" != "N" ]]; then
                gh auth login
            fi
        fi

        if gh auth status &>/dev/null; then
            gh_repo="${MY_GITHUB_USER:-dannybrown37}/password-store"
            if gh repo clone "${gh_repo}" ~/.password-store; then
                echo "Cloned password-store via gh"
                cloned="1"
            else
                echo "gh couldn't clone ${gh_repo} -- wrong account, or no access? Falling back."
            fi
        fi
    fi

    if [ -z "${cloned}" ]; then
        store_remote="${PASSWORD_STORE_REMOTE:-}"
        if [ -z "${store_remote}" ]; then
            read -rp "Git remote for your private password-store (blank to skip): " store_remote
        fi
        if [ -n "${store_remote}" ]; then
            git clone "${store_remote}" ~/.password-store &&
                echo "Cloned password-store" &&
                cloned="1"
        fi
    fi

    if [ -z "${cloned}" ]; then
        echo "Skipped password-store clone -- run 'gh auth login' and re-run this script, set PASSWORD_STORE_REMOTE and re-run, or run 'pass init <gpg-id>' manually"
    fi
else
    echo "password-store already present"
fi

# Was hardcoded to ~/projects/dotfiles, which silently did nothing from a clone
# anywhere else.
git -C "${dotfiles}" config core.hooksPath githooks &&
    echo "Configured git hooks -- commits run pre-commit"
