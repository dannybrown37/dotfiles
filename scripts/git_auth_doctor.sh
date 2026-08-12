#!/usr/bin/env bash
# Diagnoses why a GitHub push is refused. Handles both transports: an SSH remote
# gets an SSH diagnosis (and a nudge back to HTTPS, which is what the rest of
# this setup is built around), an HTTPS remote gets its credential chain walked.
# Read-only — does not install or modify anything.
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
readonly SSH_TIMEOUT=5

# Which account the personal credential helper is expected to serve. Every
# other owner is a work/org remote, where gh answering is the correct outcome.
readonly PERSONAL_GITHUB_USER="${MY_GITHUB_USER:-dannybrown37}"

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

# Header files are CRLF-terminated, so every extracted value gets the \r stripped
# — a status of $'200\r' compares equal to nothing and silently fails every check.
header_status() {
    awk 'toupper($1) ~ /^HTTP/ {code=$2} END {sub(/\r$/, "", code); print code}' "$1"
}

# Last match wins: curl -L appends a header block per hop, and only the final
# response's headers describe what actually answered.
header_value() {
    awk -v want="$1" -F': ' '
        tolower($1) == want { sub(/\r$/, "", $2); value = $2 }
        END { print value }
    ' "$2"
}

# A credential is a secret in whichever slot it arrives in — GitHub accepts a
# PAT as the username, and credential-store entries written from a tokenised
# clone URL put it there. Never print one just because it came back as a name.
redact_if_secret() {
    local value="$1"
    if [[ "$value" =~ ^gh[pousr]_ || "${#value}" -ge 40 ]]; then
        token_fingerprint "$value"
    else
        printf '%s' "$value"
    fi
}

# Splits any GitHub-ish remote into host/owner/repo. Host aliases from
# ~/.ssh/config are the standard two-account SSH setup, so the host is whatever
# the URL says, not an assumed github.com.
parse_remote() {
    local url="$1" rest=""
    if [[ "$url" =~ ^https?://([^/]+)/(.+)$ ]]; then
        remote_host="${BASH_REMATCH[1]}"
        rest="${BASH_REMATCH[2]}"
    elif [[ "$url" =~ ^ssh://([^@/]+@)?([^:/]+)(:[0-9]+)?/(.+)$ ]]; then
        remote_host="${BASH_REMATCH[2]}"
        rest="${BASH_REMATCH[4]}"
    elif [[ "$url" =~ ^([^@/]+@)?([^:/]+):(.+)$ ]]; then
        remote_host="${BASH_REMATCH[2]}"
        rest="${BASH_REMATCH[3]}"
    else
        return 1
    fi

    rest="${rest%/}"
    rest="${rest%.git}"
    [[ "$rest" == */* ]] || return 1
    remote_owner="${rest%%/*}"
    remote_repo="${rest##*/}"
    [[ -n "$remote_owner" && -n "$remote_repo" ]]
}

# `ssh -G` prints the effective config for a host, which is the only way to
# learn that `github-work` is really github.com.
resolve_ssh_host() {
    local host="$1" real=""
    if command -v ssh &>/dev/null; then
        real=$(ssh -G "$host" 2>/dev/null | awk '/^hostname /{print $2; exit}')
    fi
    printf '%s' "${real:-$host}"
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
echo "  ║                        Git Auth Doctor                           ║"
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

remote_host=""
remote_owner=""
remote_repo=""
if parse_remote "$remote_url"; then
    ok "remote owner" "$remote_owner"
else
    warn "remote owner" "could not parse from $remote_url — skipping account checks"
fi

is_ssh=false
[[ "$remote_url" == https://* ]] || is_ssh=true

# The alias may point anywhere; only a host that really resolves to github.com
# gets GitHub-specific advice or API calls.
resolved_host="$remote_host"
if [[ "$is_ssh" == true && -n "$remote_host" ]]; then
    resolved_host=$(resolve_ssh_host "$remote_host")
fi

is_github=false
[[ "$resolved_host" == "github.com" ]] && is_github=true

https_url=""
if [[ "$is_github" == true && -n "$remote_owner" && -n "$remote_repo" ]]; then
    https_url="https://github.com/${remote_owner}/${remote_repo}.git"
fi

# GitHub logins are case-insensitive and the remote URL keeps whatever was
# typed, so a case difference must not flip which helper is expected.
expects_personal_helper=false
if [[ -n "$remote_owner" && "${remote_owner,,}" == "${PERSONAL_GITHUB_USER,,}" ]]; then
    expects_personal_helper=true
fi

if [[ "$is_ssh" == true ]]; then
    warn "protocol" "SSH remote — identity and tokens here are routed by HTTPS URL, so SSH bypasses all of it"
fi
if [[ "$is_github" == false ]]; then
    warn "host" "${resolved_host:-unknown} is not github.com — GitHub account checks and the HTTPS recommendation are skipped"
fi

# ── SSH remote ────────────────────────────────────────────────────────────────

# Printed twice on purpose: once beside the SSH failures that motivate it, and
# again in the summary, which is the part anyone actually reads.
recommend_https_switch() {
    [[ -n "$https_url" ]] || return 0
    echo ""
    printf "  ⇢   Switch this remote to HTTPS — one command:\n\n"
    printf "          git remote set-url origin %s\n" "$https_url"
}

check_ssh_agent() {
    if ! command -v ssh-add &>/dev/null; then
        warn "ssh-agent" "ssh-add not installed — cannot inspect loaded keys"
        return
    fi

    local keys status
    keys=$(ssh-add -l 2>&1)
    status=$?

    case "$status" in
    0) ok "ssh-agent" "$(printf '%s\n' "$keys" | grep -c .) key(s) loaded" ;;
    1) fail "ssh-agent" "agent running but no identities — run: ssh-add ~/.ssh/id_ed25519" ;;
    *) fail "ssh-agent" "no agent reachable — WSL does not persist one across shells. Run: eval \"\$(ssh-agent -s)\" && ssh-add ~/.ssh/id_ed25519" ;;
    esac
}

check_ssh_auth() {
    if ! command -v ssh &>/dev/null; then
        warn "ssh auth" "ssh not installed"
        return
    fi

    # Probe the host the remote actually names. Probing github.com instead would
    # clear a broken `github-work` alias, or condemn a working one, since each
    # alias can carry its own IdentityFile.
    local target="${remote_host:-github.com}"

    # BatchMode keeps a missing key or unknown host from blocking on a prompt;
    # host key checking is left at its default so this stays read-only.
    local output login
    output=$(ssh -T -o BatchMode=yes -o ConnectTimeout="$SSH_TIMEOUT" "git@${target}" 2>&1)

    if [[ "$output" == *"successfully authenticated"* ]]; then
        login="${output#*Hi }"
        login="${login%%!*}"
        ok "ssh auth" "$target accepted the key as '$login'"
    else
        fail "ssh auth" "$(printf '%s' "$output" | tr '\n' ' ' | cut -c1-88)"
    fi
}

# Counted as a delta, not a snapshot of the running total: an earlier failure
# (an old git, a missing include) would otherwise be blamed on SSH.
ssh_failures=0
if [[ "$is_ssh" == true ]]; then
    failures_before_ssh=$FAILURES
    section "SSH remote"
    check_ssh_agent
    check_ssh_auth
    ssh_failures=$((FAILURES - failures_before_ssh))
    recommend_https_switch
fi

# ── Config resolution ─────────────────────────────────────────────────────────

if [[ "$is_ssh" == true ]]; then
    section "Config resolution (preview — how HTTPS would resolve)"
else
    section "Config resolution"
fi

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
            warn "$label" "real file, not a symlink — run: make symlinks"
        fi
    elif [[ "$include" == *private ]]; then
        warn "$label" "absent — only personal remotes have an identity here"
    else
        fail "$label" "missing — git ignores an includeIf pointing at a nonexistent file, silently. Run: make symlinks"
    fi
done

# ── Credential helper script ──────────────────────────────────────────────────

section "Credential helper script"

# Which helper *should* win depends on who owns the remote. Demanding the
# personal helper everywhere reported a broken chain on every work repo.
if [[ "$expects_personal_helper" == true ]]; then
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
        fail "helper script" "personal remote, but the personal helper is not effective (got: ${effective_helper:-none})"
    fi
elif [[ "$effective_helper" =~ git-credential-personal\.sh ]]; then
    fail "helper script" "personal helper is effective for '$remote_owner' — it would push as $PERSONAL_GITHUB_USER"
elif [[ -z "$effective_helper" ]]; then
    fail "helper script" "no helper configured for https://github.com"
else
    ok "helper script" "${effective_helper} — correct for non-personal remote '$remote_owner'"
fi

if [[ -n "${MY_GITHUB_TOKEN:-}" ]]; then
    ok "MY_GITHUB_TOKEN" "$(token_fingerprint "$MY_GITHUB_TOKEN")"
elif [[ "$expects_personal_helper" == true ]]; then
    fail "MY_GITHUB_TOKEN" "not exported — helper falls back to gh, which returns GITHUB_TOKEN (the work token). Check: grep MY_GITHUB_TOKEN config/.secrets, then: make secrets-load"
else
    warn "MY_GITHUB_TOKEN" "not exported — not needed for '$remote_owner'"
fi

if [[ -n "${GITHUB_TOKEN:-}" && -n "${MY_GITHUB_TOKEN:-}" ]]; then
    if [[ "$GITHUB_TOKEN" == "$MY_GITHUB_TOKEN" ]]; then
        warn "GITHUB_TOKEN" "identical to MY_GITHUB_TOKEN — the two accounts are not actually separated here"
    else
        ok "GITHUB_TOKEN" "distinct from MY_GITHUB_TOKEN"
    fi
fi

# ── End-to-end credential fill ────────────────────────────────────────────────

if [[ "$is_ssh" == true ]]; then
    section "End-to-end (preview — git credential fill over HTTPS)"
else
    section "End-to-end (git credential fill)"
fi

fill_request="protocol=https
host=github.com
"
if [[ -n "$remote_owner" ]]; then
    fill_request+="path=${remote_owner}/${remote_repo}
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
    ok "credential fill" "username=$(redact_if_secret "${filled_user:-<none>}")  password=$(token_fingerprint "$filled_pass")"

    filled_digest=$(token_digest "$filled_pass")
    if [[ "$expects_personal_helper" == true && -n "${MY_GITHUB_TOKEN:-}" ]]; then
        if [[ "$filled_digest" == "$(token_digest "$MY_GITHUB_TOKEN")" ]]; then
            ok "token source" "MY_GITHUB_TOKEN (personal helper answered)"
        elif [[ -n "${GITHUB_TOKEN:-}" && "$filled_digest" == "$(token_digest "$GITHUB_TOKEN")" ]]; then
            fail "token source" "GITHUB_TOKEN answered for a personal remote — the gh helper won. Check helper order above"
        else
            warn "token source" "matches neither env token — probably a cached credential from gh or osxkeychain/libsecret"
        fi
    elif [[ "$expects_personal_helper" == false ]]; then
        if [[ -n "${MY_GITHUB_TOKEN:-}" && "$filled_digest" == "$(token_digest "$MY_GITHUB_TOKEN")" ]]; then
            fail "token source" "MY_GITHUB_TOKEN answered for '$remote_owner' — the personal helper leaked onto a non-personal remote"
        elif [[ -n "${GITHUB_TOKEN:-}" && "$filled_digest" == "$(token_digest "$GITHUB_TOKEN")" ]]; then
            ok "token source" "GITHUB_TOKEN (work account — correct for '$remote_owner')"
        else
            warn "token source" "matches neither env token — probably a cached credential from gh or osxkeychain/libsecret"
        fi
    fi
fi

# ── Account identity ──────────────────────────────────────────────────────────

section "Account identity"

# The token goes through a 0600 config file rather than argv, which is world
# readable in /proc/<pid>/cmdline for the life of the request. -L follows the
# 301 GitHub answers for a renamed or transferred repo, which git push follows
# transparently and so must not be reported as a failure.
github_api() {
    local url="$1" headers="$2" config
    config=$(mktemp)
    {
        printf 'header = "Authorization: Bearer %s"\n' "$filled_pass"
        printf 'header = "Accept: application/vnd.github+json"\n'
    } >"$config"

    curl -sS -L --max-time "$API_TIMEOUT" -D "$headers" --config "$config" "$url" 2>/dev/null
    rm -f "$config"
}

if [[ "$is_github" == false ]]; then
    warn "account" "skipped — ${resolved_host:-this host} is not github.com"
elif [[ -z "$filled_pass" ]]; then
    warn "account" "skipped — no credential to resolve"
elif ! command -v curl &>/dev/null; then
    warn "account" "skipped — curl not installed"
else
    user_headers=$(mktemp)
    repo_headers=$(mktemp)
    trap 'rm -f "$user_headers" "$repo_headers"' EXIT

    user_body=$(github_api "https://api.github.com/user" "$user_headers")
    user_status=$(header_status "$user_headers")
    api_login=$(printf '%s' "$user_body" | sed -n 's/.*"login"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -n1)
    api_scopes=$(header_value "x-oauth-scopes" "$user_headers")

    if [[ "$user_status" != "200" ]]; then
        fail "account" "GitHub API returned ${user_status:-no response} — token invalid, expired, or network blocked"
    else
        ok "account" "$api_login"

        # Whole-scope match. A substring test passes 'repo:status',
        # 'read:repo_hook' and 'repo_deployment', none of which grant a push.
        scope_list=",${api_scopes// /},"
        if [[ -z "$api_scopes" ]]; then
            warn "token scopes" "none reported — fine-grained token; verify it grants Contents:write on this repo"
        elif [[ "$scope_list" == *,repo,* ]]; then
            ok "token scopes" "$api_scopes"
        elif [[ "$scope_list" == *,public_repo,* ]]; then
            warn "token scopes" "$api_scopes — 'public_repo' pushes to public repos only; a private repo will be denied"
        else
            fail "token scopes" "$api_scopes — missing 'repo', pushes over HTTPS will be denied"
        fi
    fi

    # Asking GitHub whether this token can push beats comparing the token's
    # login to the remote owner: an org repo's owner is never a user login, so
    # that comparison failed on every work repo it was ever run against.
    if [[ "$user_status" == "200" && -n "$remote_owner" ]]; then
        repo_body=$(github_api "https://api.github.com/repos/${remote_owner}/${remote_repo}" "$repo_headers")
        repo_status=$(header_status "$repo_headers")
        repo_sso=$(header_value "x-github-sso" "$repo_headers")

        case "$repo_status" in
        200)
            can_push=$(
                printf '%s' "$repo_body" | tr ',' '\n' |
                    sed -n 's/.*"push"[[:space:]]*:[[:space:]]*\(true\|false\).*/\1/p' | head -n1
            )
            if [[ "$can_push" == "true" ]]; then
                ok "repo access" "$api_login can push to ${remote_owner}/${remote_repo}"
            else
                fail "repo access" "$api_login has read-only access to ${remote_owner}/${remote_repo} — pushes will 403"
            fi
            ;;
        401 | 403 | 404)
            if [[ -n "$repo_sso" ]]; then
                fail "repo access" "$repo_status — token needs SSO authorization for '$remote_owner': $repo_sso"
            else
                fail "repo access" "$repo_status — ${remote_owner}/${remote_repo} is not reachable as '$api_login'. Wrong account, no access, or the token needs SSO authorization"
            fi
            ;;
        *)
            fail "repo access" "GitHub API returned ${repo_status:-no response} for ${remote_owner}/${remote_repo}"
            ;;
        esac
    fi
fi

# ── Summary ───────────────────────────────────────────────────────────────────

https_failures=$((FAILURES - ssh_failures))

section "Summary"

if [[ "$FAILURES" -eq 0 ]]; then
    echo "  ${PASS} Credential chain is healthy — plain 'git push' should work."
elif [[ "$is_ssh" == true && "$ssh_failures" -gt 0 && "$https_failures" -eq 0 ]]; then
    echo "  ${FAIL} SSH auth is broken, but the HTTPS chain above checks out."
    recommend_https_switch
elif [[ "$is_ssh" == true && "$ssh_failures" -gt 0 ]]; then
    echo "  ${FAIL} ${FAILURES} broken link(s) — SSH is broken and HTTPS has ${https_failures} of its own."
    echo "     Fix the HTTPS ❌ above, then switch transport:"
    recommend_https_switch
else
    echo "  ${FAIL} ${FAILURES} broken link(s) — fix the first ❌ above, then re-run."
fi
echo ""

exit 0
