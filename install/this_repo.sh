#!/usr/bin/bash

sudo apt update
sudo apt install git make -y
cd ~ || exit
mkdir projects 2>/dev/null
cd projects || exit
git clone https://www.github.com/dannybrown37/dotfiles
cd dotfiles || exit
make bash
make help
