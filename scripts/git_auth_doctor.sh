#!/usr/bin/env bash
# Walks the HTTPS credential chain for a repo's GitHub remote and reports the
# first broken link. Read-only — does not install or modify anything.
# Usage: ./scripts/git_auth_doctor.sh [repo-dir]   (default: cwd, else ~/projects/dotfiles)
#
# No `set -e`: a doctor has to keep going past a failing check to reach the
# ones after it. Failures are counted and reported in the summary instead.

set -uo pipefail

PASS="✅"
FAIL="❌"
WARN="⚠️ "
FAILURES=0

readonly MIN_GIT_VERSION="2.36" # first release with includeIf hasconfig:remote.*.url
readonly API_TIMEOUT=10

# ── Helpers ───────────────────────────────────────────────────────────────────

ok() {
    local label="$1" detail="$2"
    printf "  %s  %-32s %s\n" "$PASS" "$label" "$detail"
}

fail() {
    local label="$1" hint="$2"
    printf "  %s  %-32s %s\n" "$FAIL" "$label" "$hint"
    FAILURES=$((FAILURES + 1))
}

warn() {
    local label="$1" msg="$2"
    printf "  %s %-32s %s\n" "$WARN" "$label" "$msg"
}

section() {
    echo ""
    echo "  $1"
    printf "  %s\n" "$(printf '─%.0s' {1..70})"
}

# Tokens must never reach the terminal — a screenshot of this output should be
# safe to paste. A prefix plus a digest is enough to compare two machines.
token_fingerprint() {
    local token="$1" digest
    digest=$(printf '%s' "$token" | sha256sum | cut -c1-8)
    printf '%s…  len=%d  sha256:%s' "${token:0:4}" "${#token}" "$digest"
}

token_digest() {
    printf '%s' "$1" | sha256sum | cut -c1-16
}

version_at_least() {
    local have="$1" want="$2"
    [[ "$(printf '%s\n%s\n' "$want" "$have" | sort -V | head -n1)" == "$want" ]]
}

# ── Target repo ───────────────────────────────────────────────────────────────

repo_dir="${1:-}"
if [[ -z "$repo_dir" ]]; then
    if git rev-parse --show-toplevel &>/dev/null; then
        repo_dir=$(git rev-parse --show-toplevel)
    else
        repo_dir="${HOME}/projects/dotfiles"
    fi
fi

echo ""
echo "  ╔══════════════════════════════════════════════════════════════════╗"
echo "  ║                    Git HTTPS Auth Doctor                         ║"
echo "  ╚══════════════════════════════════════════════════════════════════╝"

if ! git -C "$repo_dir" rev-parse --git-dir &>/dev/null; then
    echo ""
    fail "repo" "$repo_dir is not a git repository"
    echo ""
    exit 1
fi

# ── Environment ───────────────────────────────────────────────────────────────

section "Environment"

git_version=$(git --version | awk '{print $3}')
if version_at_least "$git_version" "$MIN_GIT_VERSION"; then
    ok "git version" "$git_version"
else
    fail "git version" "$git_version < $MIN_GIT_VERSION — 'includeIf hasconfig:' is ignored, every identity/credential include silently no-ops"
fi

ok "repo" "$repo_dir"

remote_url=$(git -C "$repo_dir" remote get-url origin 2>/dev/null)
if [[ -z "$remote_url" ]]; then
    fail "remote origin" "no origin remote — includeIf hasconfig cannot match"
    echo ""
    exit 1
fi
ok "remote origin" "$remote_url"

if [[ "$remote_url" =~ ^https://github\.com/([^/]+)/ ]] ||
    [[ "$remote_url" =~ ^git@github\.com:([^/]+)/ ]] ||
    [[ "$remote_url" =~ ^ssh://git@github\.com/([^/]+)/ ]]; then
    remote_owner="${BASH_REMATCH[1]}"
    ok "remote owner" "$remote_owner"
else
    warn "remote owner" "could not parse from $remote_url — skipping account checks"
    remote_owner=""
fi

if [[ "$remote_url" != https://* ]]; then
    warn "protocol" "remote is not HTTPS — credential helpers do not apply to SSH"
fi

# ── Config resolution ─────────────────────────────────────────────────────────

section "Config resolution"

mapfile -t helper_lines < <(
    git -C "$repo_dir" config --show-origin --get-all credential.https://github.com.helper 2>/dev/null
)
if [[ ${#helper_lines[@]} -eq 0 ]]; then
    fail "credential helper" "none configured for https://github.com"
else
    for line in "${helper_lines[@]}"; do
        origin="${line%%$'\t'*}"
        value="${line#*$'\t'}"
        ok "helper" "${value:-<reset>}  [${origin#file:}]"
    done
fi

# The personal helper is only in play if it is the LAST entry: git tries helpers
# in order and an earlier gh helper answering first would hand back the work token.
effective_helper="${helper_lines[*]: -1}"
effective_helper="${effective_helper#*$'\t'}"

git_email=$(git -C "$repo_dir" config --get user.email 2>/dev/null)
if [[ -n "$git_email" ]]; then
    email_origin=$(git -C "$repo_dir" config --show-origin --get user.email 2>/dev/null)
    ok "user.email" "$git_email  [${email_origin%%$'\t'*}]"
else
    fail "user.email" "no includeIf matched this remote — check ~/.gitconfig include paths exist"
fi

for include in "${HOME}/.gitconfig-personal" "${HOME}/.gitconfig-private"; do
    label=".${include##*/.}"
    if [[ -e "$include" ]]; then
        if [[ -L "$include" ]]; then
            ok "$label" "→ $(readlink "$include")"
        else
            warn "$label" "real file, not a symlink — run: make bash"
        fi
    elif [[ "$include" == *private ]]; then
        warn "$label" "absent — only personal remotes have an identity here"
    else
        fail "$label" "missing — git ignores an includeIf pointing at a nonexistent file, silently. Run: make bash"
    fi
done

# ── Credential helper script ──────────────────────────────────────────────────

section "Credential helper script"

if [[ "$effective_helper" =~ ^!(.+git-credential-personal\.sh)$ ]]; then
    helper_path="${BASH_REMATCH[1]}"
    # The helper is stored with a literal ~, expanded by the shell git invokes.
    helper_path="${helper_path/#\~/$HOME}"
    if [[ ! -f "$helper_path" ]]; then
        fail "helper script" "$helper_path does not exist — dotfiles cloned to a different path?"
    elif [[ ! -x "$helper_path" ]]; then
        fail "helper script" "$helper_path is not executable — run: chmod +x $helper_path"
    else
        ok "helper script" "$helper_path"
    fi
else
    fail "helper script" "personal helper is not the effective helper for this remote (got: ${effective_helper:-none})"
fi

# This script is a child of the user's shell, so it sees exactly the exported
# vars git's helper subprocess would see. Checking here IS the subprocess test.
if [[ -n "${MY_GITHUB_TOKEN:-}" ]]; then
    ok "MY_GITHUB_TOKEN" "$(token_fingerprint "$MY_GITHUB_TOKEN")"
else
    fail "MY_GITHUB_TOKEN" "not exported — helper falls back to gh, which returns GITHUB_TOKEN (the work token). Check: grep MY_GITHUB_TOKEN config/.secrets, then: make secrets-load"
fi

if [[ -n "${GITHUB_TOKEN:-}" && -n "${MY_GITHUB_TOKEN:-}" ]]; then
    if [[ "$GITHUB_TOKEN" == "$MY_GITHUB_TOKEN" ]]; then
        warn "GITHUB_TOKEN" "identical to MY_GITHUB_TOKEN — the two accounts are not actually separated here"
    else
        ok "GITHUB_TOKEN" "distinct from MY_GITHUB_TOKEN"
    fi
fi

# ── End-to-end credential fill ────────────────────────────────────────────────

section "End-to-end (git credential fill)"

fill_request="protocol=https
host=github.com
"
if [[ -n "$remote_owner" ]]; then
    fill_request+="path=${remote_owner}/$(basename "$remote_url" .git)
"
fi

# GIT_TERMINAL_PROMPT=0 makes git fail instead of blocking on a password prompt
# when no helper answers, which is itself the diagnosis.
fill_output=$(
    printf '%s\n' "$fill_request" |
        GIT_TERMINAL_PROMPT=0 GIT_ASKPASS=true SSH_ASKPASS=true \
            git -C "$repo_dir" credential fill 2>/dev/null
)

filled_user=$(printf '%s\n' "$fill_output" | sed -n 's/^username=//p')
filled_pass=$(printf '%s\n' "$fill_output" | sed -n 's/^password=//p')

if [[ -z "$filled_pass" ]]; then
    fail "credential fill" "no helper returned a password — git would prompt (or fail) on push"
else
    ok "credential fill" "username=${filled_user:-<none>}  password=$(token_fingerprint "$filled_pass")"

    if [[ -n "${MY_GITHUB_TOKEN:-}" ]]; then
        if [[ "$(token_digest "$filled_pass")" == "$(token_digest "$MY_GITHUB_TOKEN")" ]]; then
            ok "token source" "MY_GITHUB_TOKEN (personal helper answered)"
        elif [[ -n "${GITHUB_TOKEN:-}" &&
            "$(token_digest "$filled_pass")" == "$(token_digest "$GITHUB_TOKEN")" ]]; then
            fail "token source" "GITHUB_TOKEN answered, not MY_GITHUB_TOKEN — the gh helper won. Check helper order above"
        else
            warn "token source" "matches neither env token — probably a cached credential from gh or osxkeychain/libsecret"
        fi
    fi
fi

# ── Account identity ──────────────────────────────────────────────────────────

section "Account identity"

if [[ -z "$filled_pass" ]]; then
    warn "account" "skipped — no credential to resolve"
elif ! command -v curl &>/dev/null; then
    warn "account" "skipped — curl not installed"
else
    api_headers=$(mktemp)
    trap 'rm -f "$api_headers"' EXIT

    api_body=$(
        curl -sS --max-time "$API_TIMEOUT" -D "$api_headers" \
            -H "Authorization: Bearer ${filled_pass}" \
            -H "Accept: application/vnd.github+json" \
            https://api.github.com/user 2>/dev/null
    )
    api_status=$(awk 'toupper($1) ~ /^HTTP/ {code=$2} END {print code}' "$api_headers")
    api_login=$(printf '%s' "$api_body" | sed -n 's/.*"login"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -n1)
    api_scopes=$(awk -F': ' 'tolower($1) == "x-oauth-scopes" {sub(/\r$/, "", $2); print $2}' "$api_headers")

    if [[ "$api_status" != "200" ]]; then
        fail "account" "GitHub API returned ${api_status:-no response} — token invalid, expired, or network blocked"
    elif [[ -z "$remote_owner" ]]; then
        ok "account" "$api_login (remote owner unknown, not compared)"
    elif [[ "$api_login" == "$remote_owner" ]]; then
        ok "account" "$api_login — matches remote owner"
    else
        fail "account" "token belongs to '$api_login' but remote is owned by '$remote_owner' — pushes will 403"
    fi

    if [[ "$api_status" == "200" ]]; then
        if [[ -z "$api_scopes" ]]; then
            warn "token scopes" "none reported — fine-grained token; verify it grants Contents:write on this repo"
        elif [[ "$api_scopes" == *repo* ]]; then
            ok "token scopes" "$api_scopes"
        else
            fail "token scopes" "$api_scopes — missing 'repo', pushes over HTTPS will be denied"
        fi
    fi
fi

# ── Summary ───────────────────────────────────────────────────────────────────

echo ""
if [[ "$FAILURES" -eq 0 ]]; then
    echo "  ${PASS} Credential chain is healthy — plain 'git push' should work."
else
    echo "  ${FAIL} ${FAILURES} broken link(s) — fix the first ❌ above, then re-run."
fi
echo ""

exit 0
