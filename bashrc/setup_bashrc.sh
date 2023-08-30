#!/bin/bash

script=$(readlink -f "$BASH_SOURCE")
script_path=$(dirname "$script")
default_bashrc_file="$script_path/default.bashrc"
user_bashrc_file="$HOME/.bashrc"


# Check if the default.bashrc file exists
if [ -f "$default_bashrc_file" ]; then
    while IFS= read -r line; do
        if ! grep -qF "$line" "$user_bashrc_file"; then
            echo "$line" >> $user_bashrc_file
        fi
    done < "$default_bashrc_file"
else
    echo "default.bashrc file not found."
fi
