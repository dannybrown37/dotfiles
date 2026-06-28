#!/usr/bin/env bash

# Profiling
# exec 3>&2 2>/tmp/bashrc_profile.$$
# PS4='+ $(date +%s.%N) '
# set -x

# skip .bashrc if parent is copilot
parent=$(ps -h -p $PPID -ocmd)
if [ "${parent:0:7}" = "copilot" ]; then
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
HISTSIZE=1000
HISTFILESIZE=2000
export HISTIGNORE="history:ls:pwd:exit:date:clear:,,*"

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

LS_IGNORE_PATTERNS=(
    ".git"
    ".github"
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
)
export LS_IGNORE_GLOBS=$(IFS='|'; echo "${LS_IGNORE_PATTERNS[*]}")
# shellcheck disable=SC2016
export FZF_DEFAULT_COMMAND='rg --hidden --no-ignore -l "" | grep -Ev "$(echo $LS_IGNORE_GLOBS | tr "|" "\n")" | while IFS= read -r f; do [[ "$f" == *.js && -f "${f%.js}.ts" ]] || echo "$f"; done'
touch "${DOTFILES_DIR}/config/.secrets"
source "${DOTFILES_DIR}/config/.secrets"

PATH="${DOTFILES_DIR}/bin:${HOME}/.local/bin:${PATH}"

##
## WSL Specific Setup
##

if [[ -n "${WSL_DISTRO_NAME}" || "${MSYSTEM}" = "MINGW64" ]]; then
    export ON_WINDOWS=true
    # shellcheck disable=SC2016
    export WINDOWS_USERNAME=$(powershell.exe '$env:UserName' | tr -d '\r\n')
    # source "${DOTFILES_DIR}/ahk/ahk.sh"  # Choosing not to source this given the time to run, use ahk alias
    source "${DOTFILES_DIR}/wsl/cpw.sh"
    source "${DOTFILES_DIR}/wsl/bin.sh"
    PATH="${DOTFILES_DIR}/wsl:${PATH}"
fi

##
## GNOME Specific Setup
##

if [[ -f /etc/os-release && $(grep -i 'debian' /etc/os-release) ]] && [[ "$XDG_CURRENT_DESKTOP" == "GNOME" ]]; then
    . "$DOTFILES_DIR"/config/.gnome
fi


# https://the.exa.website/docs/colour-themes
EXA_COLORS_ARRAY=(
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
export EXA_COLORS="$(tr ' ' ':' <<<"${EXA_COLORS_ARRAY[*]}")"


##
## Prompt setup: seasonal colors, system based icon, git status icon
##

rainbow() {
    local colors=("$RED" "$ORANGE" "$YELLOW" "$GREEN" "$CYAN" "$MAGENTA")
    local text="$1"
    local result=""
    local i=0
    for (( c=0; c<${#text}; c++ )); do
        result+="${colors[$((i % 6))]}${text:$c:1}"
        ((i++))
    done
    echo "$result"
}

BLUE='\[\033[01;34m\]'
CYAN='\[\033[0;36m\]'
GRAY='\[\033[1;30m\]'
GREEN='\[\033[1;32m\]'
LIGHT_CYAN='\[\033[1;36m\]'
MAGENTA='\[\033[0;35m\]'
ORANGE='\[\033[0;33m\]'
RED='\[\033[1;31m\]'
WHITE='\[\033[0;37m\]'
YELLOW='\[\033[1;33m\]'

case $(date +%b) in
Mar | Apr | May)
    COLOR1=$GREEN
    COLOR2=$CYAN
    COLOR3=$RED
    COLOR4=$MAGENTA
    ;;
Jun | Jul | Aug)
    COLOR1=$RED
    COLOR2=$ORANGE
    COLOR3=$WHITE
    COLOR4=$ORANGE
    ;;
Sep | Oct | Nov)
    COLOR1=$ORANGE
    COLOR2=$RED
    COLOR3=$ORANGE
    COLOR4=$YELLOW
    ;;
Dec | Jan | Feb)
    COLOR1=$CYAN
    COLOR2=$GRAY
    COLOR3=$BLUE
    COLOR4=$LIGHT_CYAN
    ;;
esac

if [[ "${WSL_DISTRO_NAME}" = 'kali-linux' ]]; then
    PROMPT_SYMBOL=㉿
elif [[ "${WSL_DISTRO_NAME}" = 'Debian' || ${HOSTNAME} == "debian" ]]; then
    PROMPT_SYMBOL=🐧
elif [[ "${WSL_DISTRO_NAME}" = 'Ubuntu' ]]; then
    PROMPT_SYMBOL=⚙
elif [[ "${HOSTNAME}" == *"raspberrypi"* ]]; then
    PROMPT_SYMBOL=🍓
elif [[ "${MSYSTEM}" = "MINGW64" ]]; then
    PROMPT_SYMBOL=🪟
fi

PROMPT_COMMAND=git_info_env_vars

export VIRTUAL_ENV_DISABLE_PROMPT=1
# shellcheck disable=SC2250
export PS1=$COLOR1'┌────${VIRTUAL_ENV:+'$COLOR2'($(basename $VIRTUAL_ENV))'$COLOR1'─}'$COLOR3'< \w >'$COLOR1'─'$COLOR4'{ $DEV_STACK }'$COLOR1'─[ $GIT_BRANCH$GIT_ICON'' ]\n'$COLOR1'└─'$COLOR4$PROMPT_SYMBOL$WHITE' '

##
## Functions
##

# source all files in bin directory
# these use dynamic code executed outside of their functions
for file in "$DOTFILES_DIR"/bin/*.sh; do
    [[ -f "$file" ]] && source "$file"
done

# source aws-specific functions from aws/bin.sh
source "$DOTFILES_DIR"/aws/bin.sh

function cht() {  # @doc: Query cht.sh for info on many technologies
    local technologies=$(curl -s cht.sh/:list)
    local selected=$(printf '%s\n' "${technologies[@]}" | fzf)
    if [[ -z $selected ]]; then
        return
    fi
    read -p "$selected keywords (optional): " query
    if [ -n "$query" ]; then
        curl "cht.sh/$selected/$(echo "$query" | tr ' ' '+')"
    else
        curl "cht.sh/$selected"
    fi
}

function current_git_branch() {
    local gitBranch=$(git branch 2>/dev/null | grep '\*' | sed -e 's/* //')
    if [[ $gitBranch ]]; then
        echo "$gitBranch"
        return
    fi
}

function epoch_timestamp() {  # @doc: Print the current epoch timestamp in milliseconds, copy to clipboard
    echo $(($(date +%s%N) / 1000000)) | cb
}

function generate_random_uuid_and_put_in_clipboard() {
    uuid=$(cat /proc/sys/kernel/random/uuid)
    echo "$uuid" | cb
}

function git_icon() {
    local gitBranch="$(current_git_branch)"
    if [[ $gitBranch ]]; then
        local statusCheck=$(git status 2>/dev/null)
        if [[ $statusCheck =~ 'Untracked files' ]]; then
            echo ❓ # untracked files
        elif [[ $statusCheck =~ 'Changes not staged for commit' ]]; then
            echo 🛠️ # changes made, need git add
        elif [[ $statusCheck =~ 'Changes to be committed' ]]; then
            echo ✏️  # changes added, need git commit
        elif [[ $statusCheck =~ 'Your branch is ahead' ]]; then
            echo 🚀 # staged, need git push
        elif [[ $statusCheck =~ 'working tree clean' ]]; then
            echo ✅ # in sync with remote branch
        fi
    fi
}

function git_info_env_vars() {
    export GIT_BRANCH=$(current_git_branch)
    export GIT_ICON=$(git_icon)
}

function google() { # @doc: Pop open a browser to google search results type in command line
    if [[ $# -eq 0 ]]; then
        read -p "Enter you Google query: " query
    else
        query=$*
    fi

    url "https://www.google.com/search?q=${query// /+}"
}

function note() {  # @doc: Create a note file from the command line
    ## Create notes files from the command line
    ##
    ## 0 args -- will prompt for title and content
    ## 1 arg -- will assume no content desired
    ## 2 args -- first title, second content
    if [[ ! -d "$NOTES_DIR" ]]; then
        mkdir "$NOTES_DIR"
    fi
    local note_title
    local note_content=""
    if [[ $# -eq 0 ]]; then
        read -p "Enter a note title to store at $NOTES_DIR: " note_title
        if [[ -z "$note_title" ]]; then
            echo "A note title is required"
            return 1
        fi
    elif [[ $# -eq 1 ]]; then
        note_title=$1
    fi
    local note_path="${NOTES_DIR}/${note_title}"
    if [[ -e "$note_path" ]]; then
        echo "Error: This note already exists!"
        return 1
    fi
    echo "Enter additional lines for file (empty input to finish):"
    while IFS= read -r line; do
        [[ -z "$line" ]] && break
        note_content+="$line"$'\n'
    done
    {
        printf "%s" "$note_content"
    } >"$note_path"
    echo "Note saved to: $note_path"
}

function notes() { # @doc: Open a note file from the command line from $NOTES_DIR using fzf
    local selected_file
    cd "$NOTES_DIR" || return
    selected_file=$(
        find . -type f -exec basename {} \; |
            fzf --preview 'cat {}' |
            sed "s/'//g"
    )
    if [[ -n "$selected_file" ]]; then
        nvim "$NOTES_DIR/$selected_file"
    fi
    cd - || return
}

function mk() {  # @doc: Create a directory and cd into it
    mkdir -p "$@" && cd "$@" || exit
}

function push() {  # @doc: Push a message to ntfy.sh at $PERSONAL_ALERT_TOPIC | push <message>
    http POST ntfy.sh/"${PERSONAL_ALERT_TOPIC}" alert="$*"
}

function push_to_topic() {  # @doc: Push a message to ntfy.sh at a topic | push_to_topic <topic> <message>
    local topic=$1
    shift
    local message=$*

    http POST ntfy.sh/"${topic}" alert="${message}"
}

function open_url_in_browser() {  # @doc: Open a URL in the browser, system-agnostic
    case $(uname -s) in
    Darwin) open='open' ;;
    MINGW*) open='start' ;;
    MSYS*) open='start' ;;
    CYGWIN*) open='cygstart' ;;
    Linux) open='xdg-open' ;;
    *) # Try to detect WSL
        if uname -r | grep -q -i microsoft; then
            open='explorer.exe'
        else
            open='xdg-open'
        fi ;;
    esac

    URL=$1

    if [[ "${URL}" != https* ]]; then
        URL="https://${URL}"
    fi
    echo "Opening ${URL} in ${open}"
    ${BROWSER:-"${open}"} "${URL}" || xdg-open "${URL}"
}

function utc_timestamp() {  # @doc: Print the current UTC timestamp in ISO format with microseconds, copy to clipboard
    date -u +"%Y-%m-%dT%H:%M:%S.%3NZ" | cb
}

##
## Alias Setup
##


if [ -f ~/.git-completion.bash ]; then
  . ~/.git-completion.bash
fi

source "$DOTFILES_DIR"/config/.bash_aliases

##
## Language-specific configuration
##

[[ -f "/home/danny/.deno/env" ]] && . "/home/danny/.deno/env"

export GOROOT="/usr/local/go"
export GOPATH="$HOME/go"
PATH="$GOPATH/bin:$GOROOT/bin:$PATH"

if [[ -f "$HOME/.cargo/env" ]]; then
    . "$HOME/.cargo/env"
fi

if [[ -f "$HOME/.atuin/bin/env" ]]; then
    . "$HOME/.atuin/bin/env"
    [[ -f ~/.bash-preexec.sh ]] && source ~/.bash-preexec.sh
    eval "$(atuin init bash)"
    if [[ -n "$ATUIN_USERNAME" && -n "$ATUIN_PASSWORD" ]]; then
        if ! atuin status 2>/dev/null | grep -q "Username: $ATUIN_USERNAME"; then
            atuin login -u "$ATUIN_USERNAME" -p "$ATUIN_PASSWORD" -k ""  >/dev/null 2>&1 || true
        fi
    fi
fi

##
## Bespoke environmental stuff
##

bind -f "${HOME}/.inputrc"

tmux source-file ~/.tmux.conf 2>/dev/null

AUTOENV_ACTIVATE_SCRIPT="$(npm root -g 2>/dev/null)"/@hyperupcall/autoenv/activate.sh
if [ -f "$AUTOENV_ACTIVATE_SCRIPT" ]; then
    source "$AUTOENV_ACTIVATE_SCRIPT"
fi

# Remove duplicates from $PATH and then export. Do not export PATH anywhere else!
PATH=$(echo "$PATH" | tr ':' '\n' | awk '!x[$0]++' | tr '\n' ':')
export PATH

# Profiling
# set +x
# exec 2>&3 3>&-
