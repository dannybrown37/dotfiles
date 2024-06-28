#!/usr/bin/bash -i

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
    pipx
    rename
    ripgrep
    shellcheck
    unzip
    wget
    zip
    zoxide
)

sudo apt update

if [[ $WSL_DISTRO_NAME = 'kali-linux' ]]; then
    apt_packages+=(eza)
else
    apt_packages+=(exa)
fi

for package in "${apt_packages[@]}"; do
    if ! dpkg -s "${package}" >/dev/null 2>&1; then
        sudo apt install -y "${package}"
    fi
done
