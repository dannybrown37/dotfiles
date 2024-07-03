#!/usr/bin/bash -i

##
## System defaults; retained setup from fresh rc file
##

case $- in
    *i*) ;;
    *) return;;
esac
HISTCONTROL=ignoreboth:erasedups
shopt -s histappend
HISTSIZE=1000
HISTFILESIZE=2000
export HISTIGNORE="ls:cd:pwd:exit:date:clear:* --help:./setup *:,,*"

shopt -s checkwinsize

if ! shopt -oq posix; then
    if [ -f /usr/share/bash-completion/bash_completion ]; then
        . /usr/share/bash-completion/bash_completion
    elif [ -f /etc/bash_completion ]; then
        . /etc/bash_completion
    fi
fi

##
## Environment variables
##

export DOTFILES_DIR="${HOME}/projects/dotfiles"

PATH="${DOTFILES_DIR}/scripts:${PATH}"

if [[ -n "${WSL_DISTRO_NAME}" || "${MSYSTEM}" = "MINGW64" ]]; then
    export ON_WINDOWS=true
    # shellcheck disable=SC2016
    export WINDOWS_USERNAME=$(powershell.exe '$env:UserName' | tr -d '\r\n')
    if [[ "${MSYSTEM}" = "MINGW64" ]]; then
        export ON_GIT_BASH=true
    fi
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
export EXA_COLORS="$(tr ' ' ':' <<< "${EXA_COLORS_ARRAY[*]}")"

touch "${DOTFILES_DIR}/config/.secrets"
source "${DOTFILES_DIR}/config/.secrets"

##
## Prompt setup: seasonal colors, system based icon, git status icon
##

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
    (Mar|Apr|May) COLOR1=$GREEN; COLOR2=$CYAN; COLOR3=$RED; COLOR4=$MAGENTA ;;
    (Jun|Jul|Aug) COLOR1=$RED; COLOR2=$ORANGE; COLOR3=$WHITE; COLOR4=$ORANGE ;;
    (Sep|Oct|Nov) COLOR1=$ORANGE; COLOR2=$YELLOW; COLOR3=$ORANGE; COLOR4=$YELLOW ;;
    (Dec|Jan|Feb) COLOR1=$CYAN; COLOR2=$GRAY; COLOR3=$BLUE; COLOR4=$LIGHT_CYAN ;;
esac

if [[ "${WSL_DISTRO_NAME}" = 'kali-linux' ]]; then
    PROMPT_SYMBOL=㉿
elif [[ "${WSL_DISTRO_NAME}" = 'Debian' ]]; then
    PROMPT_SYMBOL=🐧
elif [[ "${WSL_DISTRO_NAME}" = 'Ubuntu' ]]; then
    PROMPT_SYMBOL=⚙
elif [[ "${HOSTNAME}" == *"raspberrypi"* ]]; then
    PROMPT_SYMBOL=🍓
elif [[ "${MSYSTEM}" = "MINGW64" ]]; then
    PROMPT_SYMBOL=🪟
fi

export VIRTUAL_ENV_DISABLE_PROMPT=1  # disables (venv) prepending prompt when venv activated, handled in PS1 var below
# shellcheck disable=SC2250
export PS1=$COLOR1'┌────${VIRTUAL_ENV:+'$COLOR2'($(basename $VIRTUAL_ENV))'$COLOR1'-}'$COLOR3'('$COLOR3'\w'$COLOR3')'$COLOR1'-'$COLOR4'[$(current_git_branch)$(git_icon)'$COLOR4']\n'$COLOR1'└─'$COLOR4$PROMPT_SYMBOL$WHITE' '

##
## Functions
##


# source all files in scripts directory
# these use dynamic code executed outside of their functions
for file in "$DOTFILES_DIR"/scripts/*; do
    if [[ -f "$file" ]]; then
        source "$file"
    fi
done


buildlogs() {  # latest build logs in CLI; required arg is AWS stage
    # shellcheck disable=SC2153
    [[ $# -eq 0 ]] && dev_stage="${DEV_STAGE}" && echo "Using default stage ${DEV_STAGE}; pass an arg to override"
    [[ $# -eq 1 ]] && dev_stage=$1
    aws-azure-login -f --profile "${AWS_PROFILE}" --mode=debug
    aws s3 cp "s3://${BUILD_ARTIFACTS_BUCKET}/${dev_stage}-back-end-build-logs/$(aws s3 ls "s3://${BUILD_ARTIFACTS_BUCKET}/${dev_stage}-back-end-build-logs/" | sort -n | tail -1 | awk '{ print $4 }' )" - | zcat -
}


cht() {
    technologies=$(curl -s cht.sh/:list)

    selected=$(printf '%s\n' "${technologies[@]}" | fzf)
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


current_git_branch() {
    local gitBranch=$(git branch 2> /dev/null | sed -e "/^[^*]/d" -e "s/* \(.*\)/\1/")
    if [[ $gitBranch ]]; then
        echo "$gitBranch"
        return
    fi
}


function_history() {
    local cmd=$(history | awk '{$1=""; print $0}' | fzf)
    if [[ -n "$cmd" ]]; then
        eval "$cmd"
    fi
}


git_icon() {
    local gitBranch="$(current_git_branch)"
    if [[ $gitBranch ]]; then
        local statusCheck=$(git status 2> /dev/null)
        if [[ $statusCheck =~ 'Untracked files' ]]; then
            echo ❓  # untracked files
        elif [[ $statusCheck =~ 'Changes not staged for commit' ]]; then
            echo 🛠️  # changes made, need git add
        elif [[ $statusCheck =~ 'Changes to be committed' ]]; then
            echo ✏️  # changes added, need git commit
        elif [[ $statusCheck =~ 'Your branch is ahead' ]]; then
            echo 🚀  # staged, need git push
        elif [[ $statusCheck =~ 'working tree clean' ]]; then
            echo ✅  # in sync with remote branch
        fi
    fi
}


google() {
    if [[ $# -eq 0 ]]; then
        read -p "Enter you Google query: " query
    else
        query=$*
    fi

    explorer.exe "https://www.google.com/search?q=${query}"
}


node_project_init() {
    if [[ -n "$(ls -A)" ]]; then
        echo "WARNING: Current working directory is not empty, see the contents:"
        ls -A
        read -r -p "Directory name to create in ~/projects/ (leave blank to proceed in cwd): " project_name
        if [[ -n "${project_name}" ]]; then
            local location="${HOME}/projects/${project_name}"
            mkdir -p "${location}"
            echo "Project directory created at: ${location}"
            cd "${location}" || exit
        fi
    fi
    if [[ $(pwd) = "${HOME}/projects" || $(pwd) = "${HOME}" ]]; then
        echo "ERROR: Don't run this script in ${HOME} or ${HOME}/projects"
        return
    fi
    if [[ -d ".git" ]]; then
        echo "ERROR: A .git folder already exists in the current working directory"
        return
    fi
    yes | npx gitignore node
    npm init -y
    npm i --save-dev typescript
    git init
    mkdir src
    touch src/index.ts

    tsconfig_content=$(cat <<EOF
{
    "compilerOptions": {
        "target": "es6",
        "module": "commonjs",
        "outDir": "./dist",
        "rootDir": "./src",
        "strict": true
    }
}
EOF
)
    echo "${tsconfig_content}" > tsconfig.json
}


pip_project_init() {
    python -m venv .tempvenv
    source .tempvenv/bin/activate
    pip install cookiecutter
    cookiecutter https://www.github.com/dannybrown37/pip_package_cookiecutter
    deactivate
    rm -rf .tempvenv
}


# # # #
# open browser to particular Lambda's monitoring page
# lopen arg1 [developer stage] [AWS region] [Lambda name]
# env variables:
# LAMBDA_PATHS -- an array of paths to search for Lambda folders
# DEV_STAGE -- the name of the dev stage
open_lambda_monitoring_tab_in_browser() {
    if [[ $# -lt 3 ]]; then
        lambda_folder=$(find "${LAMBDA_PATHS[@]}" \
                        -mindepth 1 -maxdepth 1 \
                        -type d \
                        -not -path '*/node_modules*' | fzf)
        [[ -z "${lambda_folder}" ]] && echo "Error: No Lambda folder selected" && return
        lambda_name=$(basename "${lambda_folder}")
    fi
    if [[ $# -eq 0 ]]; then
        stage="${DEV_STAGE}"
        if [[ -z "${stage}" ]]; then
            echo "Error: no DEV_STAGE environment variable set or arg passed"
            exit 1
        fi
        echo "Using default stage ${DEV_STAGE}; pass an arg to override"
        aws_region="us-east-1"
        echo "Using default region us-east-1; pass an arg to override"
    elif [[ $# -eq 1 ]]; then
        stage=$1
        aws_region="us-east-1"
        echo "Using default region us-east-1; pass an arg to override"
    elif [[ $# -eq 2 ]]; then
        stage=$1
        aws_region=$2
    elif [[ $# -eq 3 ]]; then
        stage=$1
        aws_region=$2
        lambda_name=$3
    else
        echo "Error: Invalid number of arguments"
        return
    fi

    stage_title_case=$(echo "${stage}" | awk '{print toupper(substr($0, 1, 1)) tolower(substr($0, 2))}')

    if [[ ! "${lambda_name,,}" == *"demo"* ]]; then
        lambda_name="${lambda_name}${stage_title_case}"
    fi

    lambda_name=${lambda_name/demo/$stage}
    lambda_name=${lambda_name/Demo/$stage_title_case}

    url="https://${aws_region}.console.aws.amazon.com/lambda/home?region=${aws_region}#/functions/${lambda_name}?tab=monitoring"
    echo "$url"

    cmd.exe /c start "${url}" 2>/dev/null
}


mk() {
    mkdir -p "$@" && cd "$@" || exit
}


push() {
    local topic="danny_is_alerted"
    http POST ntfy.sh/"${topic}" alert="$*"
}


push_to_topic() {
    local topic=$1
    shift
    local message=$*

    http POST ntfy.sh/"${topic}" alert="${message}"
}


open_url_in_browser() {
    case $(uname -s) in
    Darwin)   open='open';;
    MINGW*)   open='start';;
    MSYS*)    open='start';;
    CYGWIN*)  open='cygstart';;
    *)  # Try to detect WSL (Windows Subsystem for Linux)
        if uname -r | grep -q -i microsoft; then
            open='explorer.exe'
        else
            open='xdg-open'
        fi;;
    esac

    URL=$1

    if [[ "${URL}" != https* ]]; then
        URL="https://${URL}"
    fi

    ${BROWSER:-"${open}"} "${URL}"
}

##
## Aliases
##

alias chrome='google-chrome 2>/dev/null &'
alias fh='function_history'
alias gg='google'
alias lopen='open_lambda_monitoring_tab_in_browser'
alias url='open_url_in_browser'

if [[ -n "${ON_WINDOWS}" ]]; then
    alias ahk='${DOTFILES_DIR}/ahk/ahk.sh'
    alias beep_c4='powershell.exe -c "[console]::beep(261, 300)"'
    alias beep_d4='powershell.exe -c "[console]::beep(294, 300)"'
    alias beep_e4='powershell.exe -c "[console]::beep(330, 300)"'
    alias beep_f4='powershell.exe -c "[console]::beep(349, 300)"'
    alias beep_g4='powershell.exe -c "[console]::beep(392, 300)"'
    alias beep_a4='powershell.exe -c "[console]::beep(440, 300)"'
    alias beep_b4='powershell.exe -c "[console]::beep(494, 300)"'
    alias beep_c5='powershell.exe -c "[console]::beep(523, 300)"'
    alias beep='beep_g4'
    alias ascend='beep_c4; beep_e4; beep_g4; beep_c5'
    alias descend='beep_c5; beep_g4; beep_e4; beep_c4'
    alias melody='beep_c5; beep_g4; beep_a4; beep_g4; beep_c4; beep_c5; beep_c4'
    alias monks='beep_a4; beep_a4; beep_g4; beep_g4; beep_f4; beep_e4; beep_a4; beep_c5; beep_b4; beep_a4; beep_a4; beep_g4; beep_a4'
fi

if dpkg-query -W -f='${Status}' zoxide 2>/dev/null | grep -q "ok installed"; then
    eval "$(zoxide init bash)"
    alias cd='z'
fi

if dpkg-query -W -f='${Status}' exa eza 2>/dev/null | grep -q "ok installed"; then
    # https://the.exa.website/features/filtering
    ls_ignore_globs=".git|.github|node_modules|__pycache__|*.pyc|.pytest_cache|.ruff_cache|*.js.map|*.egg-info"
    alias l="exa --ignore-glob=\${ls_ignore_globs}"
    alias ll="exa -alh --ignore-glob=\${ls_ignore_globs}"
    alias lsa="exa -alh"
    alias ls=ll
    alias tree="exa --tree -la --ignore-glob=\".git\""
fi

if dpkg-query -W -f='${Status}' bat 2>/dev/null | grep -q "ok installed"; then
    alias cat="batcat"
    alias bat="batcat"
    alias pcat="batcat -p"
    alias pbat="batcat -p"
fi

##
## Language-specific configuration
##

export PYENV_ROOT="$HOME/.pyenv"
PATH="$PYENV_ROOT/bin:$PATH"
if command -v pyenv 1>/dev/null 2>&1; then
    eval "$(pyenv init --path)"
    eval "$(pyenv virtualenv-init -)"
fi

export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"

export GOROOT="/usr/local/go"
export GOPATH="$HOME/go"
PATH="$GOPATH/bin:$GOROOT/bin:$PATH"

if [[ -f "$HOME/.cargo/env" ]]; then
    . "$HOME/.cargo/env"
fi

##
## Bespoke environmental stuff
##

# In lieu of a symlink between WSL and Windows, just sync settings.json on each shell reboot
"$DOTFILES_DIR"/.vscode/sync_vsc_settings.sh >/dev/null 2>&1

# Remove duplicates from $PATH and then export. Do not export PATH anywhere else!
PATH=$(echo "$PATH" | tr ':' '\n' | awk '!x[$0]++' | tr '\n' ':')
export PATH
