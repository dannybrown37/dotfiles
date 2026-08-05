#!/usr/bin/env bash

##
## Install latest version of terraform (skips if already current)
##

set -euo pipefail

sudo apt-get install -y -qq jq unzip

latest_version=$(curl -s https://api.releases.hashicorp.com/v1/releases/terraform/latest | jq -r '.version')
current_version=$(terraform version -json 2>/dev/null | jq -r '.terraform_version' || echo "none")

if [[ "${current_version}" == "${latest_version}" ]]; then
    echo "terraform ${latest_version} already installed"
    exit 0
fi

echo "Installing terraform ${current_version} → ${latest_version}"

arch=$(dpkg --print-architecture)

tmp_dir=$(mktemp -d)
trap 'rm -rf "${tmp_dir}"' EXIT

curl -sLo "${tmp_dir}/terraform.zip" \
    "https://releases.hashicorp.com/terraform/${latest_version}/terraform_${latest_version}_linux_${arch}.zip"

unzip -q "${tmp_dir}/terraform.zip" terraform -d "${tmp_dir}"
sudo install "${tmp_dir}/terraform" /usr/local/bin/terraform

echo "terraform ${latest_version} installed at $(command -v terraform)"
