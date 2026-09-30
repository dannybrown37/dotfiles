#!/usr/bin/env bash
## @extra docker-credential-desktop.exe | Docker Desktop on the Windows host (WSL integration)

##
## The docker CLI inside WSL is injected by Docker Desktop's WSL integration,
## so the Windows app is what gets installed.
##
## The marker binary reaches PATH via WSL's Windows PATH interop, and only
## Docker Desktop ships it, so docker-engine's CLI can't pass for it.
##

set -euo pipefail

readonly DESKTOP_EXE="/mnt/c/Program Files/Docker/Docker/Docker Desktop.exe"

if command -v dockerd &>/dev/null; then
    echo "Docker Engine is installed in this distro; it and Docker Desktop fight over the docker CLI and socket." >&2
    echo "Remove it first: sudo apt purge docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin docker-ce-rootless-extras" >&2
    exit 1
fi

if ! grep -qi microsoft /proc/version 2>/dev/null; then
    echo "docker-desktop targets WSL; on native Linux use: just extras docker-engine" >&2
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
