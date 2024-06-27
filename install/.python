#!/usr/bin/bash -i

##
## Install dependencies pyenv needs to build individual python versions
##

sudo apt update

pyenv_build_depencies=(
    build-essential
    libbz2-dev
    libffi-dev
    liblzma-dev
    libncurses5-dev
    libncursesw5-dev
    libreadline-dev
    libssl-dev
    libsqlite3-dev
    llvm
    lzma-dev
    tk-dev
    xz-utils
    zlib1g-dev
)
for package in "${pyenv_build_depencies[@]}"; do
    if ! dpkg -s "${package}" >/dev/null 2>&1; then
        sudo apt install -y "${package}"
    fi
done


##
## Install Pyenv
##

curl pyenv.run | bash

##
## Copy pyenv configuration to .bashrc file
##

# shellcheck disable=SC2016
PYENV_SETUP='
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
if command -v pyenv 1>/dev/null 2>&1; then
    eval "$(pyenv init --path)"
fi
eval "$(pyenv virtualenv-init -)"
'

needs_update=false
while IFS= read -r line; do
    if ! grep -Fxq "${line}" ~/.bashrc; then
        needs_update=true
        break
    fi
done <<< "${PYENV_SETUP}"

if [[ "${needs_update}" = true ]]; then
    echo "${PYENV_SETUP}" >> ~/.bashrc
    echo "pyenv config variables added to .bashrc"
else
    echo "pyenv config variables already exist in .bashrc"
fi

# shellcheck disable=SC1090
. ~/.bashrc

##
## Install 3.12, set it as global Python version
##

pyenv install -N 3.12
pyenv global 3.12


##
## Install pipx and desirable pipx packages to have globally
##

if [[ -n "${WSL_DISTRO_NAME}" ]]; then
    sudo apt install -y pipx
    pipx ensurepath
else  # Git Bash
    python3 -m pip install --user pipx
    python3 -m pipx ensurepath
fi

pipx_packages=(
    poetry
    pre-commit
    cookiecutter
    ruff
)

for package in "${pipx_packages[@]}"; do
    pipx install "${package}"
done

##
## Configure symlink for global ruff config
##

# shellcheck disable=SC2128
this_file=$(readlink -f "${BASH_SOURCE}")
ruff_toml_dir=$(dirname "${this_file}")/../config
ruff_toml_file="${ruff_toml_dir}/.ruff.toml"

ln -s "${ruff_toml_file}" "${HOME}/.ruff.toml"

echo "Symlink created between ${ruff_toml_file} and ${HOME}/.ruff.toml"

# shellcheck disable=SC1090
. ~/.bashrc
