#!/usr/bin/env bash

##
##  Sync bash profile with packages and symlinks
##  This script is designed to be idempotent and can be run multiple times
##
apt_packages=(
    asciinema
    bash-completion
    bat
    cowsay
    curl
    faker
    fortune
    fzf
    git
    gh
    httpie
    jq
    make
    man-db
    lolcat
    neofetch
    openssh-server
    pass
    pipx
    rename
    ripgrep
    shellcheck
    shfmt
    tldr
    tmux
    unzip
    wget
    xclip
    zip
)

sudo apt -y update
sudo apt -y upgrade

for package in "${apt_packages[@]}"; do
    if ! dpkg -s "${package}" >/dev/null 2>&1; then
        sudo apt install -y "${package}"
    fi
done

##
## Install eza (modern ls replacement, community fork of exa)
## Not in default Debian/Ubuntu repos; install via cargo
##

if ! command -v eza &>/dev/null; then
    cargo install eza
else
    echo "eza is already installed on this system"
fi

##
## Install eza (modern ls replacement, community fork of exa)
## Not in default Debian/Ubuntu repos; requires the gierens apt repo
##

if ! command -v eza &>/dev/null; then
    sudo mkdir -p /etc/apt/keyrings
    wget -qO- https://raw.githubusercontent.com/eza-community/eza/main/deb.asc | sudo gpg --dearmor -o /etc/apt/keyrings/gierens.gpg
    echo "deb [signed-by=/etc/apt/keyrings/gierens.gpg] http://deb.gierens.de stable main" | sudo tee /etc/apt/sources.list.d/gierens.list
    sudo chmod 644 /etc/apt/keyrings/gierens.gpg /etc/apt/sources.list.d/gierens.list
    sudo apt update
    sudo apt install -y eza
else
    echo "eza is already installed on this system"
fi

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

if command -v google-chrome >/dev/null 2>&1; then
    echo "Google Chrome is already installed on this system"
else
    wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
    sudo dpkg -i google-chrome-stable_current_amd64.deb
    sudo apt-get -y install -f
    rm google-chrome-stable_current_amd64.deb
fi


##
## Clone tmux plugin manager
##

if [[ ! -d "${HOME}/.tmux/plugins/tpm" ]]; then
    git clone https://github.com/tmux-plugins/tpm ~/.tmux/plugins/tpm
else
    echo "tmux plugin manager is already installed on this system"
fi

##
## misc installs
##

curl -o ~/.git-completion.bash https://raw.githubusercontent.com/git/git/master/contrib/completion/git-completion.bash

gh extension install dlvhdr/gh-dash

##
## Install croc file sharing tool
##

if [[ ! -f "${HOME}/.local/bin/croc" ]]; then
    curl https://getcroc.schollz.com | bash
fi


###
### Install atuin shell history manager
###

curl --proto '=https' --tlsv1.2 -LsSf https://setup.atuin.sh | sh
curl https://raw.githubusercontent.com/rcaloras/bash-preexec/master/bash-preexec.sh -o ~/.bash-preexec.sh
atuin init bash

###
### Create symlinks for various config/dotfiles
###

ln -s ~/projects/dotfiles/config/.gitconfig ~/.gitconfig &&
    echo "Symlinked .gitconfig"

ln -s ~/projects/dotfiles/config/.gitignore_global ~/.gitignore_global &&
    echo "Symlinked .gitignore_global"

if [[ ! -f "${HOME}/.bashrc.og.bak" ]]; then
    mv ~/.bashrc ~/.bashrc.og.bak
    echo "Backed up original .bashrc to ~/.bashrc.og.bak"
fi
ln -s ~/projects/dotfiles/config/.bashrc ~/.bashrc &&
    echo "Symlinked .bashrc"

ln -s ~/projects/dotfiles/config/.ruff.toml ~/.ruff.toml &&
    echo "Symlinked .ruff.toml"

ln -s ~/projects/dotfiles/config/.eslintrc ~/.eslintrc &&
    echo "Symlinked .eslintrc"

ln -s ~/projects/dotfiles/config/.inputrc ~/.inputrc &&
    echo "Symlinked .inputrc"

ln -s ~/projects/dotfiles/config/.tmux.conf ~/.tmux.conf &&
    echo "Symlinked .tmux.conf"

if [ ! -L "${HOME}/.password-store" ]; then
    ln -s ~/projects/dotfiles/pass ~/.password-store
    echo "Symlinked pass/ to ~/.password-store"
else
    echo "password-store has already been symlinked"
fi

if [ ! -L "${HOME}/.config/nvim" ]; then
    mkdir ~/.config
    ln -s ~/projects/dotfiles/nvim ~/.config/nvim &&
        echo "Symlinked nvim config to ~/.config/nvim"
else
    echo "nvim config has already been symlinked"
fi
