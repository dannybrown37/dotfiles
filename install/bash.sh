#!/usr/bin/bash

apt_packages=(
    bash-completion
    bat
    curl
    fzf
    git
    httpie
    jq
    make
    man-db
    neofetch
    openssh-server
    pass
    pipx
    rename
    ripgrep
    shellcheck
    unzip
    wget
    zip
)

sudo apt update
sudo apt upgrade

if [[ "${WSL_DISTRO_NAME}" = 'kali-linux' ]]; then
    apt_packages+=(eza)
else
    apt_packages+=(exa)
fi

for package in "${apt_packages[@]}"; do
    if ! dpkg -s "${package}" >/dev/null 2>&1; then
        sudo apt install -y "${package}"
    fi
done

##
## Install zoxide, per creator, Debian/Ubuntu have old versions in apt
## https://github.com/ajeetdsouza/zoxide/issues/694#issuecomment-1946069618
##

if [[ ! -f "${HOME}/.local/bin/zoxide" ]]; then
    curl -sS https://raw.githubusercontent.com/ajeetdsouza/zoxide/main/install.sh | bash
else
    echo "zoxide is already installed on this system"
fi

##
## Install programs with wget
##

if command -v google-chrome > /dev/null 2>&1; then
    echo "Google Chrome is already installed on this system"
else
    wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
    sudo dpkg -i google-chrome-stable_current_amd64.deb
    sudo apt-get install -f
    rm google-chrome-stable_current_amd64.deb
fi

##
## Install Neovim from appimage
##

curl -LO https://github.com/neovim/neovim/releases/latest/download/nvim.appimage
chmod u+x nvim.appimage
./nvim.appimage
./nvim.appimage --appimage-extract
./squashfs-root/AppRun --version
sudo mv squashfs-root /
sudo ln -s /squashfs-root/AppRun /usr/bin/nvim
nvim --version

###
### Create symlinks for various config/dotfiles
###

ln -s ~/projects/dotfiles/config/.gitconfig ~/.gitconfig \
&& echo "Symlinked .gitconfig"

ln -s ~/projects/dotfiles/config/.gitignore_global ~/.gitignore_global \
&& echo "Symlinked .gitignore_global"

if [[ ! -f "${HOME}/.bashrc.og.bak" ]]; then
    mv ~/.bashrc ~/.bashrc.og.bak
    echo "Backed up original .bashrc to ~/.bashrc.og.bak"
fi
ln -s ~/projects/dotfiles/config/.bashrc ~/.bashrc \
&& echo "Symlinked .bashrc"

ln -s ~/projects/dotfiles/config/.ruff.toml ~/.ruff.toml \
&& echo "Symlinked .ruff.toml"

ln -s ~/projects/dotfiles/config/.eslintrc ~/.eslintrc \
&& echo "Symlinked .eslintrc"

if [ ! -L "${HOME}/.password-store" ]; then
    ln -s ~/projects/dotfiles/pass ~/.password-store
    echo "Symlinked pass/ to ~/.password-store"
else
    echo "password-store has already been symlinked"
fi

if [ ! -L "${HOME}/.config/nvim" ]; then
    ln -s ~/projects/dotfiles/nvim ~/.config/nvim \
    && echo "Symlinked nvim config to ~/.config/nvim"
else
    echo "nvim config has already been symlinked"
fi
