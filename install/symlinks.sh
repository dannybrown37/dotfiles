#!/usr/bin/env bash
## @just 13 Start Here | Symlink every tracked config into $HOME (idempotent, no network)

##
## The whole config-symlink sweep, in one target. Split out of the bootstrap
## script because this is the part you actually re-run -- every time a new file
## lands in config/ -- and it should not cost an `apt upgrade` plus a dozen
## downloads to do it. Needs no network, no sudo, and is idempotent.
##
## `link_config` itself lives in link_config.sh so lazygit.sh and spotify.sh can
## source the function without running this sweep.
##

# shellcheck source=install/link_config.sh
source "$(dirname "${BASH_SOURCE[0]}")/link_config.sh"

dotfiles="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Deliberately no `set -e`: link_config returns 1 when it refuses to clobber a
# real file, and one hand-written ~/.gitconfig should not hide the state of
# every other link. Report them all, fail at the end.
failures=0

for name in .gitconfig .gitignore_global .ruff.toml .eslintrc .inputrc \
    .gitconfig-personal .tmux.conf; do
    link_config "${dotfiles}/config/${name}" "${HOME}/${name}" || ((failures++))
done

# The distro .bashrc is a real file on a fresh machine; move it aside so
# link_config isn't refusing to clobber it on every run. The `-f .bashrc` test
# matters: without it a HOME that has no .bashrc at all (a container, a fresh
# user) runs `mv` on nothing and then claims it backed the file up.
if [[ -f "${HOME}/.bashrc" && ! -L "${HOME}/.bashrc" && ! -f "${HOME}/.bashrc.og.bak" ]]; then
    mv ~/.bashrc ~/.bashrc.og.bak
    echo "Backed up original .bashrc to ~/.bashrc.og.bak"
fi
link_config "${dotfiles}/config/.bashrc" "${HOME}/.bashrc" || ((failures++))

# Untracked: holds any non-personal git identity. Delivered by secrets-load, so
# only symlink it once the file actually exists.
if [[ -f "${dotfiles}/config/.gitconfig-private" ]]; then
    link_config "${dotfiles}/config/.gitconfig-private" \
        "${HOME}/.gitconfig-private" || ((failures++))
fi

link_config "${dotfiles}/config/CLAUDE.md" "${HOME}/.claude/CLAUDE.md" || ((failures++))
link_config "${dotfiles}/nvim" "${HOME}/.config/nvim" || ((failures++))
link_config "${dotfiles}/config/starship.toml" \
    "${HOME}/.config/starship.toml" || ((failures++))

if ((failures > 0)); then
    echo "${failures} config symlink(s) not created -- see above." >&2
    # The Makefile sources its targets, so `return` is the correct exit here;
    # `|| exit` covers being run as `bash install/symlinks.sh` from bootstrap,
    # where a top-level `return` is an error. Also keeps a hand-typed
    # `source install/symlinks.sh` from closing the user's terminal.
    # shellcheck disable=SC2317  # reachable when executed rather than sourced
    return 1 2>/dev/null || exit 1
fi
