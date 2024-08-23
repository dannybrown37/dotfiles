#!/usr/bin/env bash
# shellcheck disable=SC1091

##
## This script is used to create a virtual environment and install dependencies
## for a Python script in the current directory. It detects WSL vs Git Bash and
## activates the virtual environment accordingly. It detects pyproject.toml or
## requirements.txt and installs the dependencies accordingly.
##

install_requirements() {
    pip install $1 --require-virtualenv || {
        echo "Failed to activate the virtual environment. Deleting .venv..."
        rm -rf .venv
        exit 1
    }
}

activate_venv() {
    if [ -n "$WSL_DISTRO_NAME" ]; then
        . .venv/bin/activate
    else
        . .venv/Scripts/activate
    fi
}

pyvenv() {
    if [[ "$VIRTUAL_ENV" != "" ]]; then
        . deactivate
    fi

    if [ ! -d ".venv" ]; then

        echo "Creating a virtual environment and installing dependencies..."

        python3 -m venv .venv

        activate_venv

        pip install --upgrade pip

        if [ -f "pyproject.toml" ]; then
            install_requirements "-e ."
        elif [ -f "requirements.txt" ]; then
            install_requirements "-r requirements.txt"
        else
            echo "Neither pyproject.toml nor requirements.txt found."
            exit 1
        fi

    fi

    activate_venv
}
