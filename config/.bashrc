#!/usr/bin/env bash

# skip .bashrc if parent is copilot
if [[ -r "/proc/${PPID}/comm" && $(<"/proc/${PPID}/comm") == "copilot"* ]]; then
    return
fi

##
## Started as system defaults; slightly tweaked over time

case $- in
*i*) ;;
*) return ;; # only run this file in interactive shell
esac
HISTCONTROL=ignoreboth:erasedups
shopt -s histappend
shopt -s expand_aliases
HISTSIZE=100000
HISTFILESIZE=200000
export HISTIGNORE="history:ls:pwd:exit:date:clear:,,*"
export HISTTIMEFORMAT="%F %T  "

shopt -s checkwinsize

if ! shopt -oq posix; then
    if [[ $- == *i* ]]; then
        if [ -f /usr/share/bash-completion/bash_completion ]; then
            . /usr/share/bash-completion/bash_completion
        else
            [ -f /etc/bash_completion ] && . /etc/bash_completion
        fi
    fi
fi

##
## Environment variables
##

export DOTFILES_DIR="${HOME}/projects/dotfiles"
export NOTES_DIR="${HOME}/notes"
export EDITOR="nvim"
export MANPAGER="sh -c 'col -bx | batcat -l man -p'"

# Without this, gpg cannot find a terminal to prompt on when it is invoked with
# stdin redirected -- which is how git hooks run pass. Guarded because `tty`
# prints "not a tty" (rather than failing) in non-interactive shells.
if [[ -t 0 ]]; then
    GPG_TTY="$(tty)"
    export GPG_TTY
fi

LS_IGNORE_PATTERNS=(
    ".git"
    "node_modules"
    "__pycache__"
    "*.pyc"
    ".pytest_cache"
    ".ruff_cache"
    "*.js.map"
    "*.egg-info"
    ".venv"
    "build"
    "dist"
    "venv"
    ".next"
)
export LS_IGNORE_GLOBS=$(IFS='|'; echo "${LS_IGNORE_PATTERNS[*]}")
# shellcheck disable=SC2016
export FZF_DEFAULT_COMMAND='rg --hidden --no-ignore -l "" | grep -Ev "$(echo $LS_IGNORE_GLOBS | tr "|" "\n")" | while IFS= read -r f; do [[ "$f" == *.js && -f "${f%.js}.ts" ]] || echo "$f"; done'

PATH="${DOTFILES_DIR}/bin:${HOME}/.local/bin:${PATH}"

##
## WSL Specific Setup
##

if [[ -n "${WSL_DISTRO_NAME}" ]]; then
    export ON_WINDOWS=true
    # shellcheck disable=SC2016
    [[ -z "${WINDOWS_USERNAME:-}" ]] && export WINDOWS_USERNAME=$(powershell.exe '$env:UserName' | tr -d '\r\n')
    # source "${DOTFILES_DIR}/ahk/ahk.sh"  # Choosing not to source this given the time to run, use ahk alias
    source "${DOTFILES_DIR}/wsl/cpw.sh"
    source "${DOTFILES_DIR}/wsl/bin.sh"
    PATH="${DOTFILES_DIR}/wsl:${PATH}"
fi

##
## GNOME Specific Setup
##

if grep -qi 'debian' /etc/os-release 2>/dev/null && [[ "$XDG_CURRENT_DESKTOP" == "GNOME" ]]; then
    . "$DOTFILES_DIR"/config/.gnome
fi


### Color-code ls / tree output based on file type / patterns / et al ###
# https://github.com/eza-community/eza/blob/main/docs/Colour-Themes.md
EZA_COLORS_ARRAY=(
    "package.json=30;47"
    "pyproject.toml=30;47"
    "serverless.yml=30;47"
    ".bashrc=30;47"

    ".gitignore=35;40;1"
    ".gitattributes=35;40;1"
    ".gitmodules=35;40;1"
    ".gitconfig=35;40;1"

    "*rc.json=30;47;1"
    "jest.config.js=30;47;1"
    ".pre-commit-config.yaml=30;47;1"
    "*config*.json=30;47;1"
    ".shellcheckrc=30;47;1"
    ".env=30;47;1"

    ".ruff.toml=31;40"

    "swagger*.yml=31;40;1"

    "buildspec.yml=30;40;1"
    "package-lock.json=30;40;1"
    "*secrets*=30;40;1"
)
export EZA_COLORS="$(tr ' ' ':' <<<"${EZA_COLORS_ARRAY[*]}")"


### Prompt setup is just starship these days ###

eval "$(starship init bash)"


### Sourcing of various local and third-party tools/configuration ###

for file in "$DOTFILES_DIR"/bin/*.sh; do
    [[ -f "$file" ]] && source "$file"
done

source "$DOTFILES_DIR"/aws/bin.sh

touch "${DOTFILES_DIR}/config/.secrets"
. "${DOTFILES_DIR}/config/.secrets"

[[ -f ~/.git-completion.bash ]] && . "$HOME/.git-completion.bash"

. "$DOTFILES_DIR"/config/.bash_aliases

bind -f "${HOME}/.inputrc"
[[ -f "/home/danny/.deno/env" ]] && . "$HOME/.deno/env"
[[ -f "$HOME/.cargo/env" ]] && . "$HOME/.cargo/env"

export GOROOT="/usr/local/go"
export GOPATH="$HOME/go"
PATH="$GOPATH/bin:$GOROOT/bin:$PATH"


if [[ -f "$HOME/.atuin/bin/env" ]]; then
    . "$HOME/.atuin/bin/env"
    [[ -f "$HOME/.bash-preexec.sh" ]] && source "$HOME/.bash-preexec.sh"
    eval "$(atuin init bash)"
    
    # Load custom preexec/precmd hooks after bash-preexec is available
    [[ -f "${DOTFILES_DIR}/config/.bash_preexec_hooks" ]] && source "${DOTFILES_DIR}/config/.bash_preexec_hooks"
fi

# Remove duplicates from $PATH and then export. Do not export PATH anywhere else!
PATH=$(echo "$PATH" | tr ':' '\n' | awk '!x[$0]++' | tr '\n' ':')
export PATH


### Between-Enters Timer ###

# This shows a cool grayed-out 1.234s timer after each entered command to show how long it took
# Low-cost profiling built-in for every command, plus sanity checking how much time long-running commands *really* take
# shellcheck disable=SC2016  # usage here is intentional, we want the literal string to be evaluated at runtime
PS0='$(echo "$EPOCHREALTIME" > /tmp/_bt_$$)'

_bt_pc_mark() { _bt_pc_start=$EPOCHREALTIME; }

_bt_show() {
    local now=$EPOCHREALTIME
    local f="/tmp/_bt_$$"
    if [[ -f "$f" ]]; then
        awk "BEGIN{printf \"  \033[2m%.3fs\033[0m\n\",($now-$(< "$f"))}"
        rm -f "$f"
    elif [[ -n "${_bt_pc_start:-}" ]]; then
        awk "BEGIN{printf \"  \033[2m%.3fs\033[0m\n\",($now-${_bt_pc_start})}"
    fi
}

[[ "${PROMPT_COMMAND[*]}" != *_bt_pc_mark* ]] && PROMPT_COMMAND=("_bt_pc_mark" "${PROMPT_COMMAND[@]}")
[[ "${PROMPT_COMMAND[*]}" != *_bt_show* ]] && PROMPT_COMMAND+=($'\n''_bt_show')
