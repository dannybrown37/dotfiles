#!/usr/bin/env bash

##
## Verify a tool is fully wired into this dotfiles repo.
##
## Usage: check-tool-wiring.sh <tool> [--apt-package <pkg>] [--no-stub]
##
## --apt-package  when the apt package name differs (fd-find -> fd)
## --no-stub      for language runtimes and action-only Make targets that
##                deliberately have no passthrough stub
##
## Tools arrive three ways, and they need different wiring:
##   dedicated  install/<tool>.sh + Make target + .PHONY + help entry
##   apt        listed in install/apt_packages.sh, no target of its own
##   bundled    built by a shared script (eza via install/bash.sh)
## All three still need a stub in bin/stubs.sh and audit coverage.
##

set -euo pipefail

readonly EXIT_FAILED_CHECKS=1
readonly EXIT_USAGE=2

readonly PASS="✅"
readonly FAIL="❌"
readonly SKIP="➖"

failures=0

usage() {
    echo "usage: check-tool-wiring.sh <tool> [--apt-package <pkg>]" \
        "[--no-stub]" >&2
    exit "${EXIT_USAGE}"
}

pass() {
    printf "  %s  %-20s %s\n" "${PASS}" "$1" "$2"
}

fail() {
    printf "  %s  %-20s %s\n" "${FAIL}" "$1" "$2"
    failures=$((failures + 1))
}

skip() {
    printf "  %s  %-20s %s\n" "${SKIP}" "$1" "n/a — $2"
}

tool=""
apt_package=""
require_stub=true

while [[ $# -gt 0 ]]; do
    case "$1" in
    --apt-package)
        [[ $# -ge 2 ]] || usage
        apt_package="$2"
        shift 2
        ;;
    --no-stub)
        require_stub=false
        shift
        ;;
    -h | --help)
        usage
        ;;
    -*)
        echo "unknown option: $1" >&2
        usage
        ;;
    *)
        [[ -z "${tool}" ]] || usage
        tool="$1"
        shift
        ;;
    esac
done

[[ -n "${tool}" ]] || usage

root="${DOTFILES_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
readonly root

readonly makefile="${root}/Makefile"
readonly stubs="${root}/bin/stubs.sh"
readonly audit="${root}/scripts/dotfiles_audit.sh"
readonly apt_list="${root}/install/apt_packages.sh"
readonly install_script="${root}/install/${tool}.sh"

# The apt package name often differs from the command (fd-find -> fd), so
# callers pass it explicitly rather than us guessing.
apt_name="${apt_package:-${tool}}"

in_apt_list() {
    [[ -f "${apt_list}" ]] || return 1
    grep -qE "^[[:space:]]*${apt_name}[[:space:]]*$" "${apt_list}"
}

# eza and friends have no script of their own -- a shared installer builds
# them -- so fall back to searching the other install scripts by name.
find_bundling_script() {
    local candidate
    for candidate in "${root}"/install/*.sh; do
        [[ -f "${candidate}" ]] || continue
        [[ "${candidate}" == "${install_script}" ]] && continue
        if grep -qE "(^|[^[:alnum:]_-])${tool}([^[:alnum:]_-]|$)" \
            "${candidate}"; then
            basename "${candidate}"
            return 0
        fi
    done
    return 1
}

bundled_by=""

if [[ -f "${install_script}" ]]; then
    mode="dedicated"
elif in_apt_list; then
    mode="apt"
elif bundled_by="$(find_bundling_script)"; then
    mode="bundled"
else
    mode="unknown"
fi

echo ""
echo "  Wiring check: ${tool}  (${mode})"
echo ""

case "${mode}" in
dedicated)
    pass "install path" "install/${tool}.sh"
    ;;
apt)
    pass "install path" "apt_packages.sh (${apt_name})"
    ;;
bundled)
    pass "install path" "install/${bundled_by}"
    ;;
unknown)
    fail "install path" \
        "not found — if apt-installed, pass --apt-package <pkg>"
    ;;
esac

check_make_wiring() {
    if grep -qE "^${tool}:" "${makefile}"; then
        pass "make target" "${tool}:"
    else
        fail "make target" "no '${tool}:' target in Makefile"
    fi

    if grep -E '^\.PHONY:' "${makefile}" | grep -qE "[[:space:]]${tool}([[:space:]]|$)"; then
        pass ".PHONY entry" "listed"
    else
        fail ".PHONY entry" "'${tool}' missing from .PHONY line"
    fi

    # help output is what sync-readme-make.sh copies into the README, so a
    # target without a help line is invisible to both `make help` and docs.
    if grep -E '^\s*@echo' "${makefile}" | grep -qE "\"[[:space:]]+${tool}[[:space:]]"; then
        pass "make help entry" "documented"
    else
        fail "make help entry" "no '@echo' help line mentioning ${tool}"
    fi
}

if [[ "${mode}" == "dedicated" ]]; then
    check_make_wiring
else
    skip "make target" "installed without a dedicated target"
    skip ".PHONY entry" "installed without a dedicated target"
    skip "make help entry" "installed without a dedicated target"
fi

if [[ "${require_stub}" == false ]]; then
    skip "stubs.sh stub" "--no-stub"
elif [[ -f "${stubs}" ]] && grep -qE "^${tool}\(\)" "${stubs}"; then
    pass "stubs.sh stub" "present"
else
    fail "stubs.sh stub" "add '${tool}() { command ${tool} \"\$@\"; }'"
fi

# apt packages are audited in bulk by iterating apt_packages.sh, so being on
# that list already counts as coverage.
if in_apt_list; then
    pass "audit entry" "covered via apt_packages.sh"
elif [[ -f "${audit}" ]] && grep -qE "(check|check_apt)[[:space:]]+\"?${tool}\"?" "${audit}"; then
    pass "audit entry" "explicit check"
else
    fail "audit entry" "add a check to scripts/dotfiles_audit.sh"
fi

echo ""

if [[ "${failures}" -gt 0 ]]; then
    echo "  ${failures} check(s) failed"
    echo ""
    exit "${EXIT_FAILED_CHECKS}"
fi

echo "  all checks passed"
echo ""
