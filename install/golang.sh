#!/usr/bin/bash -i

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


##
## Copy golang configuration to .bashrc file if it's not already there
##

# shellcheck disable=SC2016
GOLANG_SETUP='
export GOROOT=/usr/local/go
export GOPATH=$HOME/go
export PATH=$GOPATH/bin:$GOROOT/bin:$PATH
'

needs_update=false
while IFS= read -r line; do
    if ! grep -Fxq "${line}" ~/.bashrc; then
        needs_update=true
        break
    fi
done <<< "${GOLANG_SETUP}"

if [[ "${needs_update}" = true ]]; then
    echo "${GOLANG_SETUP}" >> ~/.bashrc
    echo "golang config variables added to .bashrc"
else
    echo "golang config variables already exist in .bashrc"
fi

# shellcheck disable=SC1090
. ~/.bashrc