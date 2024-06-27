#!/usr/bin/env bash

usage() {
    echo "Usage: $0 [--install <arg>]"
    echo "  --install <arg>   Install the application with argument <arg>"
    echo "Valid args:"
    echo "  python"
    echo "  node"
    echo "  golang"
    echo "  rust"
    echo "  vscode"
    echo "  all"
    exit 1
}

root_dir=$(dirname $(readlink -f "${BASH_SOURCE[0]}"))

if [[ "$1" = "--help" ]]; then
    usage
fi

if [ "$1" = "--install" ]; then
    if [ $# -gt 1 ]; then
        INSTALL_ARG="$2"
    else
        echo "Error: --install requires an argument"
        usage
    fi
else
    echo "Error: Unknown option: $1"
    usage
fi

source $root_dir/install/.bash

if [[ "$INSTALL_ARG" = "all" || "$INSTALL_ARG" = "python" ]]; then
    source $root_dir/install/.python
fi

if [[ "$INSTALL_ARG" = "all" || "$INSTALL_ARG" = "node" ]]; then
    source $root_dir/install/.node
fi

if [[ "$INSTALL_ARG" = "all" || "$INSTALL_ARG" = "golang" ]]; then
    source $root_dir/install/.golang
fi

if [[ "$INSTALL_ARG" = "all" || "$INSTALL_ARG" = "rust" ]]; then
    source $root_dir/install/.rust
fi

if [[ "$INSTALL_ARG" = "all" || "$INSTALL_ARG" = "vscode" ]]; then
    source $root_dir/vscode/vsc_setup.sh
fi

source $root_dir/bash/profile.sh

source ~/.bashrc

echo "dotfiles setup complete!"
