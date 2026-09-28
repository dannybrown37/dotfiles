## GitHub Repo Merge Settings

ghautomerge() {  # @doc Enable auto-merge + auto-delete head branches: ghautomerge [owner/repo]
    local repo="${1:-}"
    local args=(--enable-auto-merge --delete-branch-on-merge)
    if [[ -n "${repo}" ]]; then
        gh repo edit "${repo}" "${args[@]}" || return 1
    else
        gh repo edit "${args[@]}" || return 1
    fi
    gh api "repos/${repo:-{owner\}/{repo\}}" --jq '{repo: .full_name, allow_auto_merge, delete_branch_on_merge}'
}
