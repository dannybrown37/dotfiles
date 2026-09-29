#!/usr/bin/env bash

##
## install_release_binary <binary> <tarball-url> [version]
## Puts a prebuilt binary from a GitHub release tarball into /usr/local/bin.
## Without <version>, skips if <binary> is already on PATH. With it, skips only
## if `<binary> --version` already reports it, so a bumped pin in versions.sh
## upgrades machines that have an older copy.
##
## Library only -- no `## @just` header. Exists so bootstrap never compiles from
## crates.io: `cargo install` of just, eza and git-absorb took most of a cold run.
##

install_release_binary() {
    local binary="$1"
    local url="$2"
    local version="${3:-}"
    local bin_dir="${RELEASE_BIN_DIR:-/usr/local/bin}"

    if command -v "${binary}" &>/dev/null; then
        if [[ -z "${version}" ]]; then
            echo "${binary} is already installed on this system"
            return 0
        fi
        if "${binary}" --version 2>/dev/null | grep -qF "${version}"; then
            echo "${binary} ${version} is already installed on this system"
            return 0
        fi
        echo "Upgrading ${binary} to ${version}"
    fi

    local tmp_dir
    tmp_dir=$(mktemp -d)
    curl -fsSL "${url}" | tar -xz -C "${tmp_dir}"
    # Tarballs differ in layout: some nest the binary in a versioned directory.
    sudo install "$(find "${tmp_dir}" -type f -name "${binary}" -print -quit)" "${bin_dir}/${binary}"
    rm -rf "${tmp_dir}"
    hash -r
    echo "${binary} installed at $(command -v "${binary}")"
}
