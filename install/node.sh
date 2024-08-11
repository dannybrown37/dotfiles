#!/usr/bin/env bash

##
## Install nvm and set up Node 18 as global version
##

curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
source "${HOME}/.bashrc"
export NVM_DIR="${HOME}/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
nvm install 18
nvm use 18

##
## Install global npm packages
##

global_npm_packages=(
    git-open
    typescript
    ts-node
    fast-pr
    '@hyperupcall/autoenv'
)

for package in "${global_npm_packages[@]}"; do
    npm install --global "${package}"
done
