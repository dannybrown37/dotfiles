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

rm -rf "${HOME}/.pyenv" 2>/dev/null
curl pyenv.run | bash
PATH="$HOME/.pyenv/bin:$PATH"
eval "$(pyenv init --path)"

##
## Install 3.12, set it as global Python version
##

pyenv install 3.12
pyenv global 3.12


##
## Ensure pipx install and desirable pipx packages to have globally
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
