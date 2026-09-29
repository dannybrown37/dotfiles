#!/usr/bin/env bash

##
## install_release_binary <binary> <tarball-url>
## Puts a prebuilt binary from a GitHub release tarball into /usr/local/bin.
## Skips if <binary> is already on PATH.
##
## Library only -- no `## @just` header. Exists so bootstrap never compiles from
## crates.io: `cargo install` of just, eza and git-absorb took most of a cold run.
##

install_release_binary() {
    local binary="$1"
    local url="$2"

    if command -v "${binary}" &>/dev/null; then
        echo "${binary} is already installed on this system"
        return 0
    fi

    local tmp_dir
    tmp_dir=$(mktemp -d)
    curl -fsSL "${url}" | tar -xz -C "${tmp_dir}"
    # Tarballs differ in layout: some nest the binary in a versioned directory.
    sudo install "$(find "${tmp_dir}" -type f -name "${binary}" -print -quit)" "/usr/local/bin/${binary}"
    rm -rf "${tmp_dir}"
    echo "${binary} installed at $(command -v "${binary}")"
}
