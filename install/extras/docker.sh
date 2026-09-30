#!/usr/bin/env bash
## @extra docker | Docker Desktop on the Windows host (WSL integration)

##
## The docker CLI inside WSL is injected by Docker Desktop's WSL integration,
## so the Windows app is what gets installed; bin/docker.sh assumes it.
##

set -euo pipefail

readonly DESKTOP_EXE="/mnt/c/Program Files/Docker/Docker/Docker Desktop.exe"

if ! grep -qi microsoft /proc/version 2>/dev/null; then
    echo "docker extra targets WSL + Docker Desktop; on native Linux install Docker Engine instead" >&2
    exit 1
fi

if [[ -f "${DESKTOP_EXE}" ]]; then
    echo "Docker Desktop is already installed on this system"
else
    winget.exe install --id Docker.DockerDesktop --exact \
        --accept-source-agreements --accept-package-agreements
fi

if ! command -v docker &>/dev/null; then
    echo "Next: open Docker Desktop -> Settings -> Resources -> WSL integration, enable this distro, then run: docker-up"
fi
