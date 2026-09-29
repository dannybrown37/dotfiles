#!/usr/bin/env bash
set -euo pipefail
## @just 40 Environment-Specific | Install Gnome extensions (dash-to-dock, just-perfection)

# pipx rather than uv: --system-site-packages gives gext the distro's python3-gi.
sudo apt install -y pipx
pipx install gnome-extensions-cli --system-site-packages

gext install dash-to-dock@micxgx.gmail.com
gext enable dash-to-dock@micxgx.gmail.com

gext install just-perfection-desktop@just-perfection
gext enable just-perfection-desktop@just-perfection
