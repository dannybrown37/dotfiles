## GitHub Actions In-Progress Run Watcher

unalias ghwatch 2>/dev/null || true

ghwatch() { # @doc github-action-watch: watch the current repo's in-progress CI | ghwatch [--any-branch]
    local any_branch=0
    case "${1:-}" in
    --any-branch) any_branch=1 ;;
    "") ;;
    *)
        echo "Usage: ghwatch [--any-branch]" >&2
        return 1
        ;;
    esac

    local repo_path
    if ! repo_path="$(git rev-parse --show-toplevel 2>/dev/null)"; then
        echo "Not inside a git repository." >&2
        return 1
    fi

    local gh_repo
    gh_repo="$(cd "${repo_path}" && gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null || echo "")"
    if [[ -z "${gh_repo}" ]]; then
        echo "Error: Could not determine GitHub repo. Authenticate with: gh auth login" >&2
        return 1
    fi

    local -a filters=(-R "${gh_repo}" --limit 20)
    if ((any_branch == 0)); then
        local branch
        branch="$(git -C "${repo_path}" branch --show-current)"
        if [[ -z "${branch}" ]]; then
            echo "Detached HEAD; use: ghwatch --any-branch" >&2
            return 1
        fi
        filters+=(--branch "${branch}")
    fi

    # Older `gh` has no `--status` flag, so filter client-side. Anything not "completed"
    # is still live (queued, in_progress, waiting, requested, pending).
    local runs
    runs="$(gh run list "${filters[@]}" --json databaseId,workflowName,headBranch,status \
        -q '.[] | select(.status != "completed")
            | "\(.databaseId)\t\(.status)\t\(.workflowName)\t\(.headBranch)"' 2>/dev/null)"

    if [[ -z "${runs}" ]]; then
        echo "No in-progress or queued runs — showing last completed run:" >&2
        echo ""
        gh run list "${filters[@]}" --limit 1 --json databaseId \
            -q '.[0].databaseId' 2>/dev/null \
            | xargs -I{} gh run view {} -R "${gh_repo}"
        return
    fi

    local run_line
    if [[ "$(echo "${runs}" | wc -l)" -gt 1 ]]; then
        run_line="$(echo "${runs}" | column -t -s $'\t' | fzf --prompt="Run> ")"
        if [[ -z "${run_line}" ]]; then
            echo "No run selected." >&2
            return 1
        fi
    else
        run_line="${runs}"
    fi

    local run_id="${run_line%%[[:space:]]*}"

    echo "👀 Watching run ${run_id} in ${gh_repo} (press ctrl+c to detach)..."
    echo ""
    gh run watch "${run_id}" -R "${gh_repo}" --exit-status || true
    echo ""
    echo "✅ Done. View: gh run view ${run_id} -R ${gh_repo}"
}
