function open_url_in_browser() {  # @doc Open a URL in the browser, system-agnostic
    case $(uname -s) in
    Darwin) open='open' ;;
    MINGW*) open='start' ;;
    MSYS*) open='start' ;;
    CYGWIN*) open='cygstart' ;;
    Linux) open='xdg-open' ;;
    *) # Try to detect WSL
        if uname -r | grep -q -i microsoft; then
            open='explorer.exe'
        else
            open='xdg-open'
        fi ;;
    esac

    URL=$1

    if [[ "${URL}" != https* ]]; then
        URL="https://${URL}"
    fi
    echo "Opening ${URL} in ${open}"
    ${BROWSER:-"${open}"} "${URL}" || xdg-open "${URL}"
}
alias url='open_url_in_browser'  # @doc Open a URL in the system browser
