#!/usr/bin/bash -i

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

# shellcheck disable=SC1090
. ~/.bashrc
