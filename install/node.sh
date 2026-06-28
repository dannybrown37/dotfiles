#!/usr/bin/env bash

##
## Install n (Node version manager) and set up Node 22
##

if ! command -v n &>/dev/null; then
    curl -fsSL https://raw.githubusercontent.com/tj/n/master/bin/n | sudo bash -s 22
    sudo npm install --global n
fi

if ! node --version 2>/dev/null | grep -q "^v22"; then
    sudo n 22
fi

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

installed=$(npm list --global --depth=0 2>/dev/null)

for package in "${global_npm_packages[@]}"; do
    if ! echo "${installed}" | grep -q "${package}"; then
        echo "Installing ${package}..."
        npm install --global "${package}"
    fi
done

echo "Node $(node --version) ready, all global packages installed"
