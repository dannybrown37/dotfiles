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

# autoenv automatically runs .env file when you cd in
curl -#fLo- 'https://raw.githubusercontent.com/hyperupcall/autoenv/master/scripts/install.sh' | sh

# install zoxide to full-on replace cd
curl -sSfL https://raw.githubusercontent.com/ajeetdsouza/zoxide/main/install.sh | sh
