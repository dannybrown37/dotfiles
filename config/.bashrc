#!/usr/bin/bash -i

##
## System defaults; retained setup from fresh rc file
##

case $- in
    *i*) ;;
    *) return;;
esac
HISTCONTROL=ignoreboth
shopt -s histappend
HISTSIZE=1000
HISTFILESIZE=2000

shopt -s checkwinsize

if ! shopt -oq posix; then
  if [ -f /usr/share/bash-completion/bash_completion ]; then
    # shellcheck disable=SC1091
    . /usr/share/bash-completion/bash_completion
  elif [ -f /etc/bash_completion ]; then
    # shellcheck disable=SC1091
    . /etc/bash_completion
  fi
fi

##
## Environment variables
##

# shellcheck disable=SC2155
export DOTFILES_DIR="${HOME}/projects/dotfiles"

if [[ -n "${WSL_DISTRO_NAME}" || "${MSYSTEM}" = "MINGW64" ]]; then
    export ON_WINDOWS=true
    # shellcheck disable=SC2155,SC2016
    export WINDOWS_USERNAME=$(powershell.exe '$env:UserName' | tr -d '\r\n')
fi

export PATH="${DOTFILES_DIR}/scripts:${HOME}/.local/bin:${PATH}"

# https://the.exa.website/docs/colour-themes
export EXA_COLORS='*.yaml=37;44:*.yml=37;44:*.json=37;42:*.ts=30;47;1:.*=33;40:package.json=30;47;1:pyproject.toml=30;47;1:package-lock.json=30;40;1:*.js=30;40;1:*.js.map=30;40;1'

touch "${DOTFILES_DIR}/.secrets"
source "${DOTFILES_DIR}/.secrets"

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
    (Jun|Jul|Aug) COLOR1=$RED; COLOR2=$ORANGE; COLOR3=$RED; COLOR4=$ORANGE ;;
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
export PS1=$COLOR1'┌────${VIRTUAL_ENV:+'$COLOR2'($(basename $VIRTUAL_ENV))'$COLOR1'-}'$COLOR3'('$COLOR3'\w'$COLOR3')'$COLOR1'-'$COLOR4'[$(git_dot)$(current_git_branch)$(git_dot)'$COLOR4']\n'$COLOR1'└─'$COLOR4$PROMPT_SYMBOL$WHITE' '

##
## Functions
##

# source all files in scripts directory
# these use dynamic code executed outside of their functions
for file in $DOTFILES_DIR/scripts/*; do
    if [[ -f "$file" ]]; then
        source "$file"
    fi
done


buildlogs() {  # latest build logs in CLI; required arg is AWS stage
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

    # shellcheck disable=SC2162
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


current_git_status() {
  local gitBranch="$(current_git_branch)"
  if [[ $gitBranch ]]; then
    local statusCheck=$(git status 2> /dev/null)
    if [[ $statusCheck =~ 'Your branch is ahead' ]]; then
      echo 'ahead'
    elif [[ $statusCheck =~ 'Changes to be committed' ]]; then
      echo 'staged'
    elif [[ $statusCheck =~ 'no changes added' ]]; then
      echo 'modified'
    elif [[ $statusCheck =~ 'working tree clean' ]]; then
      echo 'clean'
    fi
  fi
}


git_dot() {
  local gitCheck="$(current_git_branch)"
  if [[ $gitCheck ]]; then
    local gitStatus="$(current_git_status)"

    case $gitStatus in
      modified) gitStatusDot='○' ;;
      staged) gitStatusDot='◍' ;;
      *) gitStatusDot='●' ;;
    esac

    echo "$gitStatusDot"
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


function pip_project_init {
    python -m venv .tempvenv
    source .tempvenv/bin/activate
    pip install cookiecutter
    cookiecutter https://www.github.com/dannybrown37/pip_package_cookiecutter
    deactivate
    rm -rf .tempvenv
}


lopen() {  # pop open browser to particular Lambda; arg1 (opt) Lambda name; arg2 (optional) stage; arg3 (optional) AWS region
    if [[ $# -eq 0 ]]; then
        # If no arguments are passed, use fzf to select a Lambda folder
        # LAMBDA_PATHS = an array of dirs
        lambda_folder=$(find "${LAMBDA_PATHS[@]}" \
                        -mindepth 1 -maxdepth 1 \
                        -type d \
                        -not -path '*/node_modules*' | fzf)
        [[ -z "${lambda_folder}" ]] && echo "Error: No Lambda folder selected" && return
        lambda_name=$(basename "${lambda_folder}")
        stage="${DEV_STAGE}" && echo "Using default stage ${DEV_STAGE}; pass an arg to override"
        aws_region="us-east-1"
    elif [[ $# -eq 1 ]]; then
        lambda_name=$1
        stage="${DEV_STAGE}" && echo "Using default stage ${DEV_STAGE}; pass an arg to override"
        aws_region="us-east-1"
    elif [[ $# -eq 2 ]]; then
        lambda_name=$1
        stage=$2
        aws_region="us-east-1"
    elif [[ $# -eq 3 ]]; then
        lambda_name=$1
        stage=$2
        aws_region=$3
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


url() {
    case $(uname -s) in
    Darwin)   open='open';;
    MINGW*)   open='start';;
    MSYS*)    open='start';;
    CYGWIN*)  open='cygstart';;
    *)  # Try to detect WSL (Windows Subsystem for Linux)
        if uname -r | grep -q -i microsoft; then
            open='explore.exe'
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

alias rc='nvim ~/.bashrc'
alias gg='google'

if [[ -n "${ON_WINDOWS}" ]]; then
    parent_dir=$(dirname "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")")
    alias ahk='${parent_dir}/ahk/ahk.sh'
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
fi

if dpkg-query -W -f='${Status}' exa eza 2>/dev/null | grep -q "ok installed"; then
    alias l="exa"
    alias ll="exa -alh"
    alias ls=ll
    alias tree="exa --tree"
fi

if dpkg-query -W -f='${Status}' bat 2>/dev/null | grep -q "ok installed"; then
    alias cat="batcat"
    alias bat="batcat"
    alias pcat="batcat -p"
    alias pbat="batcat -p"
fi
