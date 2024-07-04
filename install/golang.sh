#!/usr/bin/bash

##
## Clear existing version of golang and install latest version
##

sudo apt update
sudo apt install -y jq

sudo rm -rf /usr/local/go
latest_version=$(wget -qO- https://golang.org/dl/?mode=json | jq -r '.[0].version')
file_name="${latest_version}.linux-amd64.tar.gz"
download_url="https://golang.org/dl/${file_name}"
echo "${latest_version} ${download_url}"
wget "${download_url}"
sudo tar -xvf "${file_name}"
sudo mv go /usr/local
rm "${file_name}"

source "${HOME}/.bashrc"
