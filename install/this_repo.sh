#!/usr/bin/bash -eufo

sudo apt update
sudo apt install git make -y
cd ~
mkdir projects 2>/dev/null
cd projects
git clone https://www.github.com/dannybrown37/dotfiles
cd dotfiles
make bash
make help
