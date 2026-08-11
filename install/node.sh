#!/usr/bin/env bash
## @make 21 Languages & Runtimes | Install Node.js environment (n, Node 22, select global packages)

##
## Install n (Node version manager) and set up Node 22
##

readonly node_major=22

if ! command -v n &>/dev/null; then
    curl -fsSL https://raw.githubusercontent.com/tj/n/master/bin/n | sudo bash -s "${node_major}"
    sudo npm install --global n
fi

if ! node --version 2>/dev/null | grep -q "^v${node_major}"; then
    sudo n "${node_major}"
fi

##
## Verify before installing anything global. Reporting success after a failed
## sudo is how nvm silently kept shadowing n, and a stale PATH would otherwise
## send the global packages below to the wrong Node.
##

if ! command -v n &>/dev/null; then
    echo "install/node.sh: n is not on PATH after install" >&2
    exit 1
fi

if [[ "$(command -v node)" == *"/.nvm/"* ]]; then
    echo "install/node.sh: node resolves to nvm ($(command -v node))." >&2
    echo "  This repo uses n. Remove ~/.nvm, start a new shell, and re-run." >&2
    exit 1
fi

if ! node --version 2>/dev/null | grep -q "^v${node_major}"; then
    echo "install/node.sh: expected Node v${node_major}, got '$(node --version 2>&1)'" >&2
    echo "  Installed at $(command -v node). A stale shell PATH is the usual cause —" >&2
    echo "  start a new shell and re-run." >&2
    exit 1
fi

##
## Install global npm packages. n keeps Node in /usr/local, so global installs
## need sudo — unlike nvm, which kept its prefix under $HOME.
##

if ! sudo npm install --global git-open; then
    echo "install/node.sh: failed to install global npm packages" >&2
    exit 1
fi

echo "Node $(node --version) ready"
