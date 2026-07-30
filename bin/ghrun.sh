## GitHub Actions Workflow Trigger & Watch

ghrun() {  # @doc github-action-run: ghrun [repo] [workflow]
    local usage="Usage: ghrun [repo] [workflow]"

    local repo_name="${1:-}"
    local workflow_name="${2:-}"

    # Find all repos with workflows
    local projects_dir="${HOME}/projects"
    local repo_path=""

    # If repo provided, find it directly
    if [[ -n "${repo_name}" ]]; then
        repo_path="${projects_dir}/${repo_name}"
        if [[ ! -d "${repo_path}/.github/workflows" ]]; then
            echo "Repo not found or has no workflows: ${repo_name}" >&2
            return 1
        fi
    elif git rev-parse --show-toplevel &>/dev/null; then
        repo_path="$(git rev-parse --show-toplevel)"
        if [[ ! -d "${repo_path}/.github/workflows" ]]; then
            echo "Repo has no workflows: ${repo_path}" >&2
            return 1
        fi
        repo_name="$(basename "${repo_path}")"
    else
        # Find all repos and let user pick with fzf
        local temp_repos
        temp_repos=$(find "${projects_dir}" -maxdepth 3 -path "*/.github/workflows" -type d 2>/dev/null | sed 's|/.github/workflows||' | grep -v node_modules | sort)

        if [[ -z "${temp_repos}" ]]; then
            echo "No repos with workflows found in ${projects_dir}" >&2
            return 1
        fi

        local selection
        selection="$(echo "${temp_repos}" | fzf --prompt="Repo> " --preview="ls -1 {}/.github/workflows/*.{yml,yaml} 2>/dev/null" --preview-window=right:30%)"
        if [[ -z "${selection}" ]]; then
            echo "No repo selected." >&2
            return 1
        fi
        repo_path="${selection}"
        repo_name="$(basename "${repo_path}")"
    fi

    # Get GitHub owner/repo from git remote
    local gh_repo
    gh_repo="$(cd "${repo_path}" && git config --get remote.origin.url 2>/dev/null || echo "")"
    if [[ -z "${gh_repo}" ]]; then
        echo "Could not determine GitHub repo from ${repo_path}" >&2
        return 1
    fi

    # Extract owner/repo from URL (handle both https and ssh)
    gh_repo="${gh_repo##*/}"
    gh_repo="${gh_repo%.git}"
    gh_repo="$(cd "${repo_path}" && git rev-parse --abbrev-ref HEAD@{upstream} 2>/dev/null | cut -d/ -f1 || echo 'origin')/$(cd "${repo_path}" && git rev-parse --abbrev-ref HEAD 2>/dev/null)..${gh_repo}"
    # Simplify: use gh to get repo
    gh_repo="$(cd "${repo_path}" && gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null || echo "")"

    if [[ -z "${gh_repo}" ]]; then
        echo "Error: Could not determine GitHub repo. Make sure you're authenticated with: gh auth login" >&2
        return 1
    fi

    # Select workflow if not provided
    if [[ -z "${workflow_name}" ]]; then
        local workflows_dir="${repo_path}/.github/workflows"
        local had_nullglob=0
        shopt -q nullglob && had_nullglob=1
        shopt -s nullglob
        local workflow_files=("${workflows_dir}"/*.yml "${workflows_dir}"/*.yaml)
        ((had_nullglob)) || shopt -u nullglob

        local selection
        selection="$(printf '%s\n' "${workflow_files[@]##*/}" | fzf --prompt="Workflow> ")"
        if [[ -z "${selection}" ]]; then
            echo "No workflow selected." >&2
            return 1
        fi
        workflow_name="${selection}"
    fi

    # Extract workflow name without extension
    local workflow_id="${workflow_name%.yml}"
    workflow_id="${workflow_id%.yaml}"

    echo "⚠️  About to trigger: ${gh_repo}/${workflow_name}"
    local confirm
    read -r -p "Proceed? [y/N] " confirm
    if [[ ! "${confirm}" =~ ^[Yy]$ ]]; then
        echo "Aborted." >&2
        return 1
    fi

    echo "🚀 Triggering: ${gh_repo}/${workflow_name}"
    echo ""

    # Trigger workflow
    if ! gh workflow run "${workflow_name}" -R "${gh_repo}"; then
        echo "❌ Failed to trigger workflow" >&2
        return 1
    fi

    # Get the run ID - it may take a moment to appear
    echo "ℹ️  Waiting for workflow to start..."
    local run_id=""
    local attempts=0
    while [[ -z "${run_id}" ]] && [[ ${attempts} -lt 10 ]]; do
        sleep 1
        run_id="$(gh run list -R "${gh_repo}" -w "${workflow_name}" --limit 1 --json databaseId -q '.[0].databaseId' 2>/dev/null)"
        ((attempts++))
    done

    if [[ -n "${run_id}" ]]; then
        echo "📊 Run ID: ${run_id}"
        echo ""
        echo "👀 Watching workflow run (press ctrl+c to detach)..."
        echo ""
        gh run watch "${run_id}" -R "${gh_repo}" --exit-status || true
        echo ""
        echo "✅ Done. View: gh run view ${run_id} -R ${gh_repo}"
    else
        echo "⚠️  Workflow triggered but couldn't get run ID"
        echo "View runs: gh run list -R ${gh_repo} -w ${workflow_name}"
    fi
}
