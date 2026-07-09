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

echo "Node $(node --version) ready"
