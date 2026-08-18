#!/usr/bin/env bash
## Test suite for bash-preexec hooks

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOOKS_FILE="${SCRIPT_DIR}/../config/.bash_preexec_hooks"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

pass_count=0
fail_count=0

pass() {
    echo -e "${GREEN}✓${NC} $1"
    ((pass_count++))
}

fail() {
    echo -e "${RED}✗${NC} $1"
    ((fail_count++))
}

# Test that hooks file exists and is sourceable
test_hooks_file_exists() {
    if [[ -f "$HOOKS_FILE" ]]; then
        pass "Hooks file exists at $HOOKS_FILE"
    else
        fail "Hooks file not found at $HOOKS_FILE"
        exit 1
    fi
}

test_hooks_file_syntax() {
    if bash -n "$HOOKS_FILE"; then
        pass "Hooks file has valid bash syntax"
    else
        fail "Hooks file has syntax errors"
    fi
}

test_hooks_file_shellcheck() {
    if command -v shellcheck &>/dev/null; then
        if shellcheck -x "$HOOKS_FILE"; then
            pass "Hooks file passes shellcheck"
        else
            fail "Hooks file has shellcheck warnings"
        fi
    else
        echo -e "${YELLOW}⊘${NC} Skipping shellcheck (not installed)"
    fi
}

# Test dangerous command detection patterns
test_aws_context_pattern() {
    if grep -q '_show_aws_context' "$HOOKS_FILE" && \
       grep -q 'AWS_PROFILE' "$HOOKS_FILE"; then
        pass "AWS context display function exists"
    else
        fail "AWS context display function incomplete"
    fi
}

# Test long-running notification uses ntfy
test_long_running_notify() {
    if grep -q '_notify_if_long_running' "$HOOKS_FILE" && \
       grep -q 'ntfy.sh' "$HOOKS_FILE"; then
        pass "Long-running command notification uses ntfy"
    else
        fail "Long-running command notification incomplete"
    fi
}

# Test auto-activation supports both nvm and n
test_auto_activation() {
    if grep -q '_auto_activate_env' "$HOOKS_FILE" && \
       grep -q '.venv/bin/activate' "$HOOKS_FILE" && \
       grep -q '.node-version' "$HOOKS_FILE"; then
        pass "Auto-activation function supports venv and Node (nvm/n)"
    else
        fail "Auto-activation function incomplete"
    fi
}

# Test that functions are added to hook arrays
test_preexec_registration() {
    local count
    count=$(grep -c 'preexec_functions+=(' "$HOOKS_FILE")
    if [[ "$count" -ge 2 ]]; then
        pass "Multiple preexec functions registered ($count found)"
    else
        fail "Expected at least 2 preexec functions, found $count"
    fi
}

test_precmd_registration() {
    local count
    count=$(grep -c 'precmd_functions+=(' "$HOOKS_FILE")
    if [[ "$count" -ge 2 ]]; then
        pass "Multiple precmd functions registered ($count found)"
    else
        fail "Expected at least 2 precmd functions, found $count"
    fi
}

# Test integration with .bashrc
test_bashrc_sources_hooks() {
    local bashrc="${SCRIPT_DIR}/../config/.bashrc"
    if grep -q '.bash_preexec_hooks' "$bashrc"; then
        pass ".bashrc sources preexec hooks file"
    else
        fail ".bashrc does not source preexec hooks file"
    fi
}

# Run all tests
echo "Testing bash-preexec hooks..."
echo

test_hooks_file_exists
test_hooks_file_syntax
test_hooks_file_shellcheck
test_aws_context_pattern
test_long_running_notify
test_auto_activation
test_preexec_registration
test_precmd_registration
test_bashrc_sources_hooks

echo
echo "Results: ${GREEN}${pass_count} passed${NC}, ${RED}${fail_count} failed${NC}"

exit $fail_count
