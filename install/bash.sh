#!/usr/bin/bash -i

apt_packages=(
    bash-completion
    bat
    curl
    exa
    fzf
    git
    httpie
    jq
    make
    man-db
    neofetch
    pipx
    rename
    ripgrep
    shellcheck
    unzip
    wget
    zip
)

sudo apt update

for package in "${apt_packages[@]}"; do
    if ! dpkg -s "${package}" >/dev/null 2>&1; then
        sudo apt install -y "${package}"
    fi
done

# autoenv automatically runs .env file when you cd in
wget --show-progress -o /dev/null -O- 'https://raw.githubusercontent.com/hyperupcall/autoenv/master/scripts/install.sh' | sh

# install zoxide to full-on replace cd
curl -sSfL https://raw.githubusercontent.com/ajeetdsouza/zoxide/main/install.sh | sh
