#!/usr/bin/env bash

##
##  Sync bash profile with packages and symlinks
##  This script is designed to be idempotent and can be run multiple times
##
# shellcheck source=install/apt_packages.sh
source "$(dirname "${BASH_SOURCE[0]}")/apt_packages.sh"

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
## Install tokei (code stats) -- v12 is last release with pre-built binaries
##

if ! command -v tokei &>/dev/null; then
    tmp_dir=$(mktemp -d)
    curl -sLo "${tmp_dir}/tokei.tar.gz" \
        "https://github.com/XAMPPRocky/tokei/releases/download/v12.1.2/tokei-x86_64-unknown-linux-gnu.tar.gz"
    tar -xf "${tmp_dir}/tokei.tar.gz" -C "${tmp_dir}"
    sudo install "${tmp_dir}/tokei" /usr/local/bin/tokei
    rm -rf "${tmp_dir}"
else
    echo "tokei is already installed on this system"
fi

##
## Install hyperfine (benchmarking tool)
##

if ! command -v hyperfine &>/dev/null; then
    hf_version=$(curl -s https://api.github.com/repos/sharkdp/hyperfine/releases/latest | jq -r '.tag_name' | sed 's/v//')
    tmp_deb=$(mktemp --suffix=.deb)
    curl -sLo "${tmp_deb}" \
        "https://github.com/sharkdp/hyperfine/releases/download/v${hf_version}/hyperfine_${hf_version}_amd64.deb"
    sudo dpkg -i "${tmp_deb}"
    rm "${tmp_deb}"
else
    echo "hyperfine is already installed on this system"
fi

##
## Install glow (markdown renderer)
##

if ! command -v glow &>/dev/null; then
    glow_version=$(curl -s https://api.github.com/repos/charmbracelet/glow/releases/latest | jq -r '.tag_name' | sed 's/v//')
    tmp_deb=$(mktemp --suffix=.deb)
    curl -sLo "${tmp_deb}" \
        "https://github.com/charmbracelet/glow/releases/download/v${glow_version}/glow_${glow_version}_amd64.deb"
    sudo dpkg -i "${tmp_deb}"
    rm "${tmp_deb}"
else
    echo "glow is already installed on this system"
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
## Install delta (syntax-highlighting git pager)
##

if ! command -v delta &>/dev/null; then
    delta_version=$(curl -s https://api.github.com/repos/dandavison/delta/releases/latest | jq -r '.tag_name')
    tmp_deb=$(mktemp --suffix=.deb)
    curl -sLo "${tmp_deb}" \
        "https://github.com/dandavison/delta/releases/download/${delta_version}/git-delta_${delta_version}_amd64.deb"
    sudo dpkg -i "${tmp_deb}"
    rm "${tmp_deb}"
else
    echo "delta already installed: $(delta --version)"
fi

##
## misc installs
##

curl -o ~/.git-completion.bash https://raw.githubusercontent.com/git/git/master/contrib/completion/git-completion.bash

gh extension install dlvhdr/gh-dash

##
## Install lazygit (TUI git client) + symlink its config
##

bash "$(dirname "${BASH_SOURCE[0]}")/lazygit.sh"

##
## Install Starship + JetBrainsMono Nerd Font (WSL to Windows)
##

bash "$(dirname "${BASH_SOURCE[0]}")/wsl_fonts.sh"

##
## Install croc file sharing tool
##

if [[ ! -f "${HOME}/.local/bin/croc" ]]; then
    curl https://getcroc.schollz.com | bash
fi


###
### Install atuin shell history manager
###

curl --proto '=https' --tlsv1.2 -LsSf https://setup.atuin.sh | sh -s -- --non-interactive
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

ln -s ~/projects/dotfiles/config/.gitconfig-personal ~/.gitconfig-personal &&
    echo "Symlinked .gitconfig-personal"

# Untracked: holds any non-personal git identity. Delivered by secrets-load, so
# only symlink it once the file actually exists.
if [ -f ~/projects/dotfiles/config/.gitconfig-private ]; then
    ln -sf ~/projects/dotfiles/config/.gitconfig-private ~/.gitconfig-private &&
        echo "Symlinked .gitconfig-private"
fi

ln -s ~/projects/dotfiles/config/.tmux.conf ~/.tmux.conf &&
    echo "Symlinked .tmux.conf"

if [ ! -d "${HOME}/.password-store" ]; then
    cloned=""

    if command -v gh &>/dev/null; then
        if ! gh auth status &>/dev/null; then
            read -rp "gh isn't logged in. Run 'gh auth login' now to clone password-store without handling a token by hand? [Y/n] " run_login
            if [[ "${run_login}" != "n" && "${run_login}" != "N" ]]; then
                gh auth login
            fi
        fi

        if gh auth status &>/dev/null; then
            gh_repo="${MY_GITHUB_USER:-dannybrown37}/password-store"
            if gh repo clone "${gh_repo}" ~/.password-store; then
                echo "Cloned password-store via gh"
                cloned="1"
            else
                echo "gh couldn't clone ${gh_repo} -- wrong account, or no access? Falling back."
            fi
        fi
    fi

    if [ -z "${cloned}" ]; then
        store_remote="${PASSWORD_STORE_REMOTE:-}"
        if [ -z "${store_remote}" ]; then
            read -rp "Git remote for your private password-store (blank to skip): " store_remote
        fi
        if [ -n "${store_remote}" ]; then
            git clone "${store_remote}" ~/.password-store &&
                echo "Cloned password-store" &&
                cloned="1"
        fi
    fi

    if [ -z "${cloned}" ]; then
        echo "Skipped password-store clone -- run 'gh auth login' and re-run this script, set PASSWORD_STORE_REMOTE and re-run, or run 'pass init <gpg-id>' manually"
    fi
else
    echo "password-store already present"
fi

git -C ~/projects/dotfiles config core.hooksPath githooks &&
    echo "Configured git hooks -- dotfiles push/pull now syncs password-store"

if [ ! -L "${HOME}/.config/nvim" ]; then
    mkdir ~/.config
    ln -s ~/projects/dotfiles/nvim ~/.config/nvim &&
        echo "Symlinked nvim config to ~/.config/nvim"
else
    echo "nvim config has already been symlinked"
fi

if [ ! -L "${HOME}/.config/starship.toml" ]; then
    ln -s ~/projects/dotfiles/config/starship.toml ~/.config/starship.toml &&
        echo "Symlinked starship.toml to ~/.config/starship.toml"
else
    echo "starship.toml has already been symlinked"
fi
