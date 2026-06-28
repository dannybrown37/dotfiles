## Git Worktree Helpers

gwt() {  # @doc git-worktree: gwt <add|list|rm|cd> [branch] [options]
    local usage="Usage: gwt <add|list|rm|cd> [branch] [options]"

    case "${1:-}" in
        add) shift; _gwt_add "$@" ;;
        list | ls) _gwt_list ;;
        rm) shift; _gwt_rm "$@" ;;
        cd) shift; _gwt_cd "$@" ;;
        *) echo "${usage}" >&2; return 1 ;;
    esac
}

_gwt_base_dir() {
    local git_root
    git_root="$(git rev-parse --show-toplevel 2>/dev/null)" || {
        echo "Error: not in a git repository" >&2
        return 1
    }
    echo "${git_root}/.worktrees"
}

_gwt_add() {
    local branch="${1:-}"
    local base_ref="${2:-HEAD}"

    if [[ -z "${branch}" ]]; then
        echo "Usage: gwt add <branch> [base-ref]" >&2
        return 1
    fi

    local base_dir
    base_dir="$(_gwt_base_dir)" || return 1
    mkdir -p "${base_dir}"

    local dir_name="${branch//\//-}"
    local worktree_path="${base_dir}/${dir_name}"

    if [[ -d "${worktree_path}" ]]; then
        echo "Worktree already exists: ${worktree_path}" >&2
        echo "Use: gwt cd ${branch}" >&2
        return 1
    fi

    if git show-ref --verify --quiet "refs/heads/${branch}"; then
        git worktree add "${worktree_path}" "${branch}"
    else
        git worktree add -b "${branch}" "${worktree_path}" "${base_ref}"
    fi

    echo ""
    _gwt_bootstrap "${worktree_path}"

    echo ""
    echo "Ready: cd ${worktree_path}"
    cd "${worktree_path}" || return 1
}

_gwt_bootstrap() {
    local wt_path="${1}"
    local git_root
    git_root="$(git rev-parse --show-toplevel 2>/dev/null)"

    echo "Bootstrapping dependencies..."

    # pre-commit: shares hooks via core.hooksPath or reinstall
    if [[ -f "${wt_path}/.pre-commit-config.yaml" ]]; then
        if command -v pre-commit &>/dev/null; then
            echo "  -> Installing pre-commit hooks"
            (cd "${wt_path}" && pre-commit install --install-hooks) 2>&1 | sed 's/^/     /'
        fi
    fi

    # Python: create venv and install deps
    if [[ -f "${wt_path}/pyproject.toml" ]] || [[ -f "${wt_path}/requirements.txt" ]]; then
        echo "  -> Setting up Python environment"
        if [[ -f "${wt_path}/pyproject.toml" ]] && command -v uv &>/dev/null; then
            (cd "${wt_path}" && uv sync) 2>&1 | sed 's/^/     /'
        elif [[ -f "${wt_path}/requirements.txt" ]]; then
            (cd "${wt_path}" && python -m venv .venv && .venv/bin/pip install -r requirements.txt -q)
        fi
    fi

    # Node: install node_modules (or symlink for speed)
    if [[ -f "${wt_path}/package.json" ]]; then
        echo "  -> Installing Node dependencies"
        if [[ -f "${wt_path}/package-lock.json" ]]; then
            (cd "${wt_path}" && npm ci --quiet) 2>&1 | sed 's/^/     /'
        elif [[ -f "${wt_path}/pnpm-lock.yaml" ]] && command -v pnpm &>/dev/null; then
            (cd "${wt_path}" && pnpm install --frozen-lockfile --quiet) 2>&1 | sed 's/^/     /'
        elif [[ -f "${wt_path}/yarn.lock" ]] && command -v yarn &>/dev/null; then
            (cd "${wt_path}" && yarn install --frozen-lockfile --quiet) 2>&1 | sed 's/^/     /'
        else
            (cd "${wt_path}" && npm install --quiet) 2>&1 | sed 's/^/     /'
        fi
    fi

    # Go: download modules
    if [[ -f "${wt_path}/go.mod" ]]; then
        echo "  -> Downloading Go modules"
        (cd "${wt_path}" && go mod download) 2>&1 | sed 's/^/     /'
    fi

    # Rust: fetch deps (don't build)
    if [[ -f "${wt_path}/Cargo.toml" ]]; then
        echo "  -> Fetching Rust dependencies"
        (cd "${wt_path}" && cargo fetch --quiet) 2>&1 | sed 's/^/     /'
    fi

    echo "  Done."
}

_gwt_list() {
    git worktree list
}

_gwt_rm() {
    local branch="${1:-}"

    if [[ -z "${branch}" ]]; then
        echo "Usage: gwt rm <branch>" >&2
        return 1
    fi

    local base_dir
    base_dir="$(_gwt_base_dir)" || return 1
    local dir_name="${branch//\//-}"
    local worktree_path="${base_dir}/${dir_name}"

    if [[ ! -d "${worktree_path}" ]]; then
        echo "No worktree found at: ${worktree_path}" >&2
        return 1
    fi

    local current_dir
    current_dir="$(pwd)"
    if [[ "${current_dir}" == "${worktree_path}"* ]]; then
        local git_root
        git_root="$(git -C "${worktree_path}" rev-parse --path-format=absolute --git-common-dir)"
        git_root="${git_root%/.git}"
        cd "${git_root}" || return 1
        echo "Moved to: ${git_root}"
    fi

    git worktree remove "${worktree_path}" --force
    echo "Removed worktree: ${worktree_path}"

    if git show-ref --verify --quiet "refs/heads/${branch}"; then
        read -rp "Delete branch '${branch}'? [y/N] " confirm
        if [[ "${confirm}" =~ ^[Yy]$ ]]; then
            git branch -D "${branch}"
        fi
    fi
}

_gwt_cd() {
    local branch="${1:-}"

    if [[ -z "${branch}" ]]; then
        local selection
        selection=$(git worktree list --porcelain \
            | grep "^worktree " \
            | sed 's/^worktree //' \
            | fzf --prompt="Worktree> ")
        if [[ -n "${selection}" ]]; then
            cd "${selection}" || return 1
        fi
        return 0
    fi

    local base_dir
    base_dir="$(_gwt_base_dir)" || return 1
    local dir_name="${branch//\//-}"
    local worktree_path="${base_dir}/${dir_name}"

    if [[ ! -d "${worktree_path}" ]]; then
        echo "No worktree found: ${worktree_path}" >&2
        echo "Available:" >&2
        _gwt_list >&2
        return 1
    fi

    cd "${worktree_path}" || return 1
}
