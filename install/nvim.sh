#!/bin/bash

##
## Install Neovim from appimage
##

if command -v nvim &>/dev/null; then
    echo "Neovim is already installed on this system"
else
    if [[ -n $WSL_DISTRO_NAME ]]; then
        echo "Installing Neovim for WSL"
        file_name="nvim.appimage"
    else
        file_name="nvim-linux-x86_64.appimage"
    fi
    curl -LO https://github.com/neovim/neovim/releases/latest/download/$file_name
    chmod u+x $file_name
    ./$file_name
    ./$file_name --appimage-extract
    ./squashfs-root/AppRun --version
    sudo mv squashfs-root /
    sudo ln -s /squashfs-root/AppRun /usr/bin/nvim
    nvim --version
    rm $file_name
fi
