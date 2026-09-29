#!/usr/bin/env bash
## @extra google-chrome | Google Chrome browser
set -euo pipefail

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
