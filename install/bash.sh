#!/usr/bin/env bash
## @just 12 Start Here | Install the Bash profile (symlinks, prompt, completion, history)

##
## The actual bash profile, which is what `make bash` always claimed to be and
## for a long time was not -- it used to also install seven CLI tools, Chrome and
## the password-store. Those are `make cli-tools`, `make chrome` and
## `make password-store` now.
##
## Everything here is either sourced by config/.bashrc at startup or is a file
## .bashrc looks for, so this and symlinks.sh together are what make a login
## shell behave like this repo intends.
##

script_dir="$(dirname "${BASH_SOURCE[0]}")"

##
## The .bashrc/.inputrc/.tmux.conf symlinks -- a bash profile with no .bashrc is
## not a profile. Idempotent, so re-running under `make bootstrap` is free.
##

bash "${script_dir}/symlinks.sh"

##
## git-completion, sourced by .bashrc:372
##

curl -o ~/.git-completion.bash \
    https://raw.githubusercontent.com/git/git/master/contrib/completion/git-completion.bash

##
## atuin shell history + bash-preexec, the hook atuin needs. Both are sourced by
## .bashrc:394-397, which also runs `atuin init bash` -- so this deliberately
## does not, it would only dump the init blob to stdout here.
##

curl --proto '=https' --tlsv1.2 -LsSf https://setup.atuin.sh | sh -s -- --non-interactive
curl https://raw.githubusercontent.com/rcaloras/bash-preexec/master/bash-preexec.sh \
    -o ~/.bash-preexec.sh

##
## Starship prompt (eval'd at .bashrc:204) + JetBrainsMono Nerd Font, which the
## prompt's glyphs need. WSL-to-Windows font install lives in that script.
##

bash "${script_dir}/wsl-fonts.sh"

##
## tmux plugin manager, for the plugins .tmux.conf declares
##

if [[ ! -d "${HOME}/.tmux/plugins/tpm" ]]; then
    git clone https://github.com/tmux-plugins/tpm ~/.tmux/plugins/tpm
else
    echo "tmux plugin manager is already installed on this system"
fi

##
## gh-dash, a gh extension rather than a standalone binary. `gh extension
## install` exits 1 with "there is already an installed extension that provides
## the dash command" on a re-run, so guard it -- this script claims to be
## idempotent.
##

if gh extension list 2>/dev/null | grep -q 'dlvhdr/gh-dash'; then
    echo "gh-dash is already installed on this system"
else
    gh extension install dlvhdr/gh-dash
fi
