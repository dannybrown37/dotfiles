#! bin/bash/

# Opens a pull request from current branch to specified branch

pr() {

    default_branch=develop

    read -p "Target branch [$default_branch]: " target_branch
    if [ -z $target_branch ]; then
        target_branch=$default_branch
    fi
    current_branch=$(parse_git_branch)
    pull_request_title="$current_branch -> $target_branch"

    non_current_branches=$(git for-each-ref --format='%(refname)' refs/heads/ | grep -v "refs/heads/$current_branch")
    commit_messages=$(git log $current_branch --oneline --not $non_current_branches)

    read -p "Enter your pull request description [each commit message in branch, one per line]: " pr_description

    json_content="{
        \"title\": \"$pull_request_title\",
        \"body\": \"$commit_messages\",
        \"head\": \"$current_branch\",
        \"base\": \"$target_branch\"
    }"

    echo "PR content: $json_content"

    repo_name=$(basename "$(git rev-parse --show-toplevel)")

    curl -X POST -H "Authorization: token $GIT_HUB_TOKEN" \
         -H "Accept: application/vnd.github.v3+json" \
         -d "$json_content" "https://api.github.com/repos/$GITHUB_USERNAME/$repo_name/pulls"
}
