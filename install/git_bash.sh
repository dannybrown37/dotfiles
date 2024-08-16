#!/usr/bin/env bash

##
## System setup for Git Bash on Windows
##

powershell.exe -Command "Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser"

# Install Scoop, a Windows package manager
powershell.exe -Command "Invoke-RestMethod -Uri https://get.scoop.sh | Invoke-Expression"

# Use powershell to install jq as admin, there will be a pop-up prompt
if ! command -v jq &> /dev/null; then
    powershell.exe -Command "Start-Process curl -ArgumentList '-L -o /usr/bin/jq.exe https://github.com/jqlang/jq/releases/latest/download/jq-win64.exe' -Verb RunAs"
else
    echo "jq is already installed"
fi

# install winget packages
winget install \
    sharkdp.bat \
    fzf \
    ezwinports.make

# manually install ripgrep
curl -LO https://github.com/BurntSushi/ripgrep/releases/download/13.0.0/ripgrep-13.0.0-x86_64-pc-windows-msvc.zip
unzip ripgrep-13.0.0-x86_64-pc-windows-msvc.zip
mkdir -p ~/bin
cd ripgrep-13.0.0-x86_64-pc-windows-msvc
cp -f rg.exe ~/bin/
cd ..
rm ripgrep-13.0.0-x86_64-pc-windows-msvc.zip
rm -rf ripgrep-13.0.0-x86_64-pc-windows-msvc

scoop install pipx
pipx ensurepath

pipx install cookiecutter \
             pre-commit


# TODO: exa?

