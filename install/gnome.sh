#!/usr/bin/env bash
## @make 40 Environment-Specific | Install Gnome extensions


pipx install gnome-extensions-cli --system-site-packages

gext install dash-to-dock@micxgx.gmail.com
gext enable dash-to-dock@micxgx.gmail.com

gext install just-perfection-desktop@just-perfection
gext enable just-perfection-desktop@just-perfection
