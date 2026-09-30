#!/usr/bin/env bash

##
## install_release_binary <binary> <tarball-url> [version]
## Puts a prebuilt binary from a GitHub release tarball into /usr/local/bin.
## Without <version>, skips if <binary> is already on PATH. With it, skips only
## if `<binary> --version` already reports it, so a bumped pin in versions.sh
## upgrades machines that have an older copy.
##
## GitHub release URLs are checked against the sha256 GitHub records for the
## asset. That catches a corrupt or swapped download, not a tampered release:
## the sum comes from the same place. Releases older than GitHub's digests
## have none, so those install with a warning.
##
## Library only -- no `## @just` header. Exists so bootstrap never compiles from
## crates.io: `cargo install` of just, eza and git-absorb took most of a cold run.
##

# Prints the asset's "sha256:<hex>", or nothing when GitHub has none.
github_asset_digest() {
    local url="$1" re='^https://github\.com/([^/]+/[^/]+)/releases/download/([^/]+)/([^/]+)$'
    [[ "${url}" =~ ${re} ]] || return 0
    local repo="${BASH_REMATCH[1]}" tag="${BASH_REMATCH[2]}" asset="${BASH_REMATCH[3]}"
    local auth=()
    [[ -z "${GH_TOKEN:-}" ]] || auth=(-H "Authorization: Bearer ${GH_TOKEN}")
    curl -fsSL "${auth[@]}" "https://api.github.com/repos/${repo}/releases/tags/${tag}" |
        jq -r --arg asset "${asset}" '.assets[] | select(.name == $asset) | .digest // empty'
}

verify_download() {
    local url="$1" file="$2" expected actual
    expected="$(github_asset_digest "${url}")"
    if [[ -z "${expected}" ]]; then
        echo "warning: no sha256 published for ${url##*/}, installing unverified" >&2
        return 0
    fi
    actual="sha256:$(sha256sum "${file}" | cut -d' ' -f1)"
    if [[ "${actual}" != "${expected}" ]]; then
        echo "sha256 mismatch for ${url##*/}: expected ${expected}, got ${actual}" >&2
        return 1
    fi
}

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
    curl -fsSLo "${tmp_dir}/release.tar.gz" "${url}"
    if ! verify_download "${url}" "${tmp_dir}/release.tar.gz"; then
        rm -rf "${tmp_dir}"
        return 1
    fi
    tar -xzf "${tmp_dir}/release.tar.gz" -C "${tmp_dir}"
    # Tarballs differ in layout: some nest the binary in a versioned directory.
    sudo install "$(find "${tmp_dir}" -type f -name "${binary}" -print -quit)" "${bin_dir}/${binary}"
    rm -rf "${tmp_dir}"
    hash -r
    echo "${binary} installed at $(command -v "${binary}")"
}
