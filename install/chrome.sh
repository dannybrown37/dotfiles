#!/usr/bin/env bash
## @just 15 Start Here | Install Google Chrome

##
## Split out of the old install/bash.sh, where a GUI browser sat between zoxide
## and the tmux plugin manager. Nothing else here needs it and it needs nothing
## else, so it is its own target.
##

if command -v google-chrome >/dev/null 2>&1; then
    echo "Google Chrome is already installed on this system"
else
    tmp_deb=$(mktemp --suffix=.deb)
    wget -qO "${tmp_deb}" \
        https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
    sudo dpkg -i "${tmp_deb}"
    # Chrome's .deb declares deps dpkg will not resolve on its own
    sudo apt-get -y install -f
    rm "${tmp_deb}"
fi
