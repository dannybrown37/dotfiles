#!/usr/bin/bash -i

cd ~ || exit
mkdir projects 2>/dev/null
cd projects || exit
git clone https://www.github.com/dannybrown37/dotfiles
cd dotfiles || exit
./setup
echo "Bash profile configured!"
echo "You can install the following development environment setups:"
echo "  ./setup --install <language>"
echo "      python"
echo "      node"
echo "      golang"
echo "      rust"
echo "      vscode"
echo "Or full the full suite:"
echo "      all"
echo
echo "Sync bash profile/apt packages at any time with '. ~/setup'"
