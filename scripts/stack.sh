#!/usr/bin/env bash
# @doc Ergonomic wrapper for GitHub stacked PRs (gh stack) | stack help

set -euo pipefail

readonly EXIT_USAGE=2
readonly STACK_WRAPPER_VERSION="0.1.0"

usage() {
    cat <<'EOF'
Usage: stack <command> [args...]

Fast shortcuts:
  stack setup              Install/upgrade gh-stack extension
  stack doctor             Verify gh auth + gh-stack extension
  stack start [args...]    gh stack init [args...]
  stack next [args...]     gh stack add [args...]
  stack show [args...]     gh stack view [args...]
  stack publish [args...]  gh stack submit [args...]
  stack ship [args...]     gh stack submit --open [args...]
  stack sync [args...]     gh stack sync [args...]
  stack land [args...]     gh stack merge [args...]

Raw passthrough:
  stack <any-gh-stack-subcommand> [args...]
EOF
}

die() {
    echo "stack: $1" >&2
    exit 1
}

ghstack_installed() {
    gh extension list | awk -F '\t' '$1=="gh stack"{found=1} END{exit(found?0:1)}'
}

require_gh() {
    command -v gh &>/dev/null || die "gh CLI not found (install GitHub CLI first)"
}

require_stack_extension() {
    ghstack_installed || die "gh-stack extension not installed (run: stack setup)"
}

stack_extension_version() {
    gh extension list | awk -F '\t' '$1=="gh stack"{print $3; exit}'
}

print_version() {
    local ext_version
    ext_version="$(stack_extension_version)"
    if [[ -n "${ext_version}" ]]; then
        echo "stack wrapper ${STACK_WRAPPER_VERSION} | gh-stack ${ext_version}"
    else
        echo "stack wrapper ${STACK_WRAPPER_VERSION} | gh-stack not installed"
    fi
}

setup_extension() {
    if ghstack_installed; then
        gh extension upgrade github/gh-stack
    else
        gh extension install github/gh-stack
    fi
}

doctor() {
    local errors=0

    if gh auth status &>/dev/null; then
        echo "✅ gh auth: ok"
    else
        echo "❌ gh auth: run 'gh auth login'" >&2
        errors=$((errors + 1))
    fi

    if ghstack_installed; then
        local ext_version
        ext_version="$(stack_extension_version)"
        echo "✅ gh-stack: ${ext_version:-installed}"
    else
        echo "❌ gh-stack: missing (run 'stack setup' or 'make ghstack')" >&2
        errors=$((errors + 1))
    fi

    if [[ "${errors}" -gt 0 ]]; then
        return 1
    fi
}

main() {
    if [[ $# -eq 0 ]]; then
        usage
        exit "${EXIT_USAGE}"
    fi

    case "${1}" in
    -h | --help | help)
        usage
        ;;
    -v | --version)
        require_gh
        print_version
        ;;
    setup)
        require_gh
        setup_extension
        ;;
    doctor)
        require_gh
        doctor
        ;;
    start)
        shift
        require_gh
        require_stack_extension
        gh stack init "$@"
        ;;
    next)
        shift
        require_gh
        require_stack_extension
        gh stack add "$@"
        ;;
    show)
        shift
        require_gh
        require_stack_extension
        gh stack view "$@"
        ;;
    publish)
        shift
        require_gh
        require_stack_extension
        gh stack submit "$@"
        ;;
    ship)
        shift
        require_gh
        require_stack_extension
        gh stack submit --open "$@"
        ;;
    sync)
        shift
        require_gh
        require_stack_extension
        gh stack sync "$@"
        ;;
    land)
        shift
        require_gh
        require_stack_extension
        gh stack merge "$@"
        ;;
    *)
        require_gh
        require_stack_extension
        gh stack "$@"
        ;;
    esac
}

main "$@"
