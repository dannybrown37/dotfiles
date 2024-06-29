#!/usr/bin/bash -i


function pip_project_init {
    python -m venv .tempvenv
    source .tempvenv/bin/activate
    pip install cookiecutter
    cookiecutter https://www.github.com/dannybrown37/pip_package_cookiecutter
    deactivate
    rm -rf .tempvenv
}
