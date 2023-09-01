#! bin/bash/

# Google things from the command line in WSL, pop up a web browser in Windows
# Use gg command -- git gud


gg() {
    if [ $# -eq 0 ]; then
        read -p "Enter you Google query: " query
    else
        query=""
        for arg in "$@"; do
            query="$query $arg"
        done
    fi

    explorer.exe "https://www.google.com/search?q=$query"

}
