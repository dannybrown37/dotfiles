#! bin/bash/

# Opens a pull request from current branch to default branch in repo

pr() {

    default_branch=$(git remote show origin | grep 'HEAD branch' | awk '{print $NF}')

    current_branch=$(parse_git_branch)
    pull_request_title="$current_branch -> $target_branch"

    non_current_branches=$(git for-each-ref --format='%(refname)' refs/heads/ | grep -v "refs/heads/$current_branch")
    commit_messages=$(git log $current_branch --oneline --not $non_current_branches)
    commit_message="Commits in pull request:\n"
    for message in "${commit_messages[@]}"; do
        commit_message+="\n* $message"
    done

    json_content="{
        \"title\": \"$pull_request_title\",
        \"body\": \"$commit_message\",
        \"head\": \"$current_branch\",
        \"base\": \"$target_branch\"
    }"
    echo "$json_content" > temp_pr.json

    repo_name=$(basename "$(git rev-parse --show-toplevel)")
    url="https://api.github.com/repos/$GITHUB_USERNAME/$repo_name/pulls"

    curl -X POST -H "Authorization: Bearer $GITHUB_TOKEN" \
         -H "Accept: application/vnd.github.v3+json" \
         -d @temp_pr.json \
         "$url"

    rm -f temp_pr.json
}
