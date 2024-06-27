#!/usr/bin/bash -i

##
## Install nvm and set up Node 18 as global version
##

curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
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
)

for package in "${global_npm_packages[@]}"; do
    npm install --global "${package}"
done

if [[ "$1" = "--oss" ]]; then
    script_dir=$(dirname "$(readlink -f "$0")")
    envvars_path="${script_dir}/../config/.envvars"
    . "${envvars_path}"
    npm config set init-author-name "${MY_NAME}"
    npm config set init-author-email "${MY_EMAIL}"
    npm config set init-author-url "${MY_GITHUB}"
    npm config set init-license "MIT"
    npm config set init-version "0.0.1"
fi
