#!/usr/bin/env bash
## @extra google-chrome | Google Chrome browser
set -euo pipefail

if command -v google-chrome >/dev/null 2>&1; then
    echo "Google Chrome is already installed on this system"
else
    tmp_dir=$(mktemp -d)
    trap 'rm -rf "${tmp_dir}"' EXIT
    curl -fsSLo "${tmp_dir}/chrome.deb" \
        https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
    # apt, not dpkg -i: the .deb declares deps dpkg won't fetch, and dpkg's
    # failure on them stopped the script before any `apt-get -f` could run.
    sudo apt-get install -y "${tmp_dir}/chrome.deb"
fi
