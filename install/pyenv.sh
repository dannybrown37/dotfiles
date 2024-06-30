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

# shellcheck disable=SC1090
. ~/.bashrc
