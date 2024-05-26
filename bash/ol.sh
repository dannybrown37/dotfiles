#!/bin/bash


start_ollama_server() {
    ollama serve &
    disown
}

stop_ollama_server() {
    # Find the PID of the ollama serve process
    SERVE_PID=$(pgrep -f 'ollama serve')
    if [ -n "$SERVE_PID" ]; then
        echo "Stopping ollama serve (PID $SERVE_PID)"
        kill "$SERVE_PID"
    fi
}

OLLAMA_OUTPUT=$(ollama 2>&1 >/dev/null)

if [[ $OLLAMA_OUTPUT =~ "command not found" ]]; then
    curl -fsSL https://ollama.com/install.sh | sh
    . "$HOME/.bashrc"
    start_ollama_server
    ollama pull codellama
else
    echo "ollama is already installed"
    start_ollama_server
fi

ollama run codellama

trap stop_ollama_server EXIT
stop_ollama_server
