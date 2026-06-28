#!/usr/bin/env bash

##
## Install latest version of golang (skips if already current)
##

sudo apt-get update -qq
sudo apt-get install -y -qq jq

latest_version=$(wget -qO- https://golang.org/dl/?mode=json | jq -r '.[0].version')
current_version=$(go version 2>/dev/null | awk '{print $3}')

if [[ "${current_version}" == "${latest_version}" ]]; then
    echo "Go ${latest_version} already installed"
    exit 0
fi

echo "Upgrading Go: ${current_version:-none} → ${latest_version}"
file_name="${latest_version}.linux-amd64.tar.gz"
download_url="https://golang.org/dl/${file_name}"

wget -q "${download_url}"
sudo rm -rf /usr/local/go
sudo tar -xf "${file_name}" -C /usr/local
rm "${file_name}"

source "${HOME}/.bashrc"
