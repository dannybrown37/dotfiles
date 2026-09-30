#!/usr/bin/env bash
set -euo pipefail
## @just 20 Languages & Runtimes | Install Python environment (uv, select uv tools)

# shellcheck source=install/versions.sh
source "$(dirname "${BASH_SOURCE[0]}")/versions.sh"

##
## Install uv
##

curl -LsSf "https://astral.sh/uv/${UV_VERSION}/install.sh" | sh

##
## Install the pinned Python and make it this machine's python3
##

# Pinned in .python-version, which `uv run` reads in CI and locally alike.
# --default installs the bare `python3` shim as well, so scripts with a
# `#!/usr/bin/env python3` shebang get the pinned interpreter rather than
# whatever the distro happens to ship.
python_version="$(cat "$(dirname "${BASH_SOURCE[0]}")/../.python-version")"
uv python install --default "${python_version}"

##
## Sync this repo's own venv, which the pre-push pytest hook runs in
##

uv sync --project "$(dirname "${BASH_SOURCE[0]}")/.."

##
## Install global Python packages with uv tool
##

uv_tool_packages=(
    cookiecutter
    bashate
)

for package in "${uv_tool_packages[@]}"; do
    uv tool install "${package}"
done

# Pinned (not left to float) so CI and local dev always run the same versions.
# Both the pin and the reasoning live in install/versions.sh; ci.yml reads the
# same file.
uv tool install "ruff==${RUFF_VERSION}"
uv tool install "prek==${PREK_VERSION}"
