#!/usr/bin/bash -i
# shellcheck disable=SC2088

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

###
### Create symlinks for various config/dotfiles
###

ln -s ~/projects/dotfiles/config/.gitconfig ~/.gitconfig
echo "Symlinked .gitconfig"

mv ~/.bashrc ~/.bashrc.og.bak
ln -s ~/projects/dotfiles/config/.bashrc ~/.bashrc
echo "Symlinked .bashrc"

ln -s ~/projects/dotfiles/config/.ruff.toml ~/.ruff.toml
echo "Symlinked .ruff.toml"
