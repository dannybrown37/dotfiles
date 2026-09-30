#!/usr/bin/env bash
## @extra dockerd | Docker Engine in this distro (apt + systemd), starts without a Windows login

##
## Steps from https://docs.docker.com/engine/install/debian/ (Ubuntu's repo
## has the same layout, so the distro ID picks the URL).
##

set -euo pipefail

readonly keyring=/etc/apt/keyrings/docker.asc
readonly packages=(docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin)

if command -v docker-credential-desktop.exe &>/dev/null; then
    echo "Docker Desktop is installed on the Windows host; it and Docker Engine fight over the docker CLI and socket." >&2
    echo "Remove it first: winget.exe uninstall --id Docker.DockerDesktop --exact" >&2
    exit 1
fi

if command -v dockerd &>/dev/null; then
    echo "Docker Engine is already installed"
else
    # shellcheck source=/dev/null
    distro_id="$(. /etc/os-release && echo "${ID}")"
    # shellcheck source=/dev/null
    codename="$(. /etc/os-release && echo "${VERSION_CODENAME}")"

    sudo apt update
    sudo apt install -y ca-certificates curl
    sudo install -m 0755 -d /etc/apt/keyrings
    sudo curl -fsSL "https://download.docker.com/linux/${distro_id}/gpg" -o "${keyring}"
    sudo chmod a+r "${keyring}"
    sudo tee /etc/apt/sources.list.d/docker.sources >/dev/null <<EOF
Types: deb
URIs: https://download.docker.com/linux/${distro_id}
Suites: ${codename}
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: ${keyring}
EOF
    sudo apt update
    sudo apt install -y "${packages[@]}"
fi

if [[ -d /run/systemd/system ]]; then
    sudo systemctl enable --now docker
else
    echo "No systemd here; start the daemon yourself (WSL: add [boot] systemd=true to /etc/wsl.conf)"
fi

# The docker group is root-equivalent; it's added so compose runs without sudo.
if [[ "$(id -u)" -ne 0 && " $(id -nG) " != *" docker "* ]]; then
    sudo usermod -aG docker "$(id -un)"
    echo "Added $(id -un) to the docker group; open a new shell for it to apply"
fi
