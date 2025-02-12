#!/usr/bin/env bash


pipx install gnome-extensions-cli --system-site-packages

gext install dash-to-dock@micxgx.gmail.com
gext enable dash-to-dock@micxgx.gmail.com

gext install just-perfection-desktop@just-perfection
gext enable just-perfection-desktop@just-perfection

git clone https://github.com/Tudmotu/gnome-shell-extension-clipboard-indicator.git ~/.local/share/gnome-shell/extensions/clipboard-indicator@tudmotu.com
gext enable clipboard-indicator@tudmotu.com
