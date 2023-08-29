#!/usr/bin/env bash

# To set this up, use:
#     alias cht=~/path/to/cht/cht.sh
#
# Now, call it with:
#
#     cht
#
# 1. Chose from a list of tools/languages from sibling .cht-sh-index.
# 2. Query for keyword(s) optional from the docs of those languages.


# Select a language or core utility from list in file
dir=$(dirname $0)
selected=$(cat $dir/.cht_sh_index | fzf)
if [[ -z $selected ]]; then
    return
fi

# Get optional keywords from the user
read -p "$selected keywords (optional): " query


# curl cht.sh with query
if [ -n "$query" ]; then
    curl cht.sh/$selected/$(echo $query | tr ' ' '+')
else
    curl cht.sh/$selected
fi
