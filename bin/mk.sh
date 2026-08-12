function mk() {  # @doc Create a directory and cd into it
    if [[ $# -eq 0 ]]; then
        echo "usage: mk <directory>" >&2
        return 1
    fi
    mkdir -p "$@" && cd "$@" || return 1
}
