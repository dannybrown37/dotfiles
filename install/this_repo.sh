#!/usr/bin/bash -i

cd ~ || exit
mkdir projects 2>/dev/null
cd projects || exit
git clone https://www.github.com/dannybrown37/dotfiles
cd dotfiles || exit
./setup
