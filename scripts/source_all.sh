#!/bin/bash


# source all files in scripts except this one itself


script_path=$(readlink -f "${BASH_SOURCE[0]}")
script_dir=$(dirname $script_path)
script_name=$(basename $script_path)

# Loop through each script file and source it
for script_file in "$script_dir"/*.sh; do
    if [[ -f "$script_file" && ! "$script_file" =~ .*"$script_name".* ]]; then
        source "$script_file"
    fi
done
