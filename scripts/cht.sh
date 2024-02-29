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


cht() {
    # shellcheck disable=SC2206
    technologies=(
        awk
        bash
        cat
        chmod
        cp
        curl
        find
        git
        golang
        grep
        head
        jq
        kill
        less
        ls
        man
        mv
        nodejs
        python
        rename
        rm
        sed
        ssh
        tail
        tar
        tr
        trap
        typescript
        xargs
    )

    # Select a language or core utility from the array
    selected=$(printf '%s\n' "${technologies[@]}" | fzf)
    if [[ -z $selected ]]; then
        return
    fi

    # Get optional keywords from the user
    read -p "$selected keywords (optional): " query

    # curl cht.sh with query
    if [ -n "$query" ]; then
        curl "cht.sh/$selected/$(echo $query | tr ' ' '+')"
    else
        curl "cht.sh/$selected"
    fi
}
