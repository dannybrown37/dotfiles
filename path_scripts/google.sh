#! bin/bash/

# Google things from the command line in WSL, pop up a web browser in Windows
# Use gg command -- git gud, go google, GooGle, et al


gg() {
    if [ $# -eq 0 ]; then
        read -p "Enter you Google query: " query
    else
        query=""
        for arg in "$@"; do
            escaped_arg=$(echo "$arg" | sed -e 's/[\/&]/\\&/g')
            query="$query $escaped_arg"
        done
    fi

    explorer.exe "https://www.google.com/search?q=$query"

}

alias google=gg
