#! bin/bash/


# Opens a pull request from current branch to default branch in repo


pr() {

    if git remote -v | grep -q "bitbucket"; then
        repo_home="bitbucket"
        if [[ -z $BITBUCKET_TOKEN ]]; then
            echo "Error: You must set your BITBUCKET_TOKEN in the environment"
            return
        fi
    elif git remote -v | grep -q "github"; then
        repo_home="github"
        if [[ -z $GITHUB_USERNAME || -z $GITHUB_TOKEN ]]; then
            echo "Error: You must set your GITHUB_USERNAME and GITHUB_TOKEN in the environment"
            return
        fi
    else
        echo "Error: Repo's remote URL is not supported. Add it or stick with GitHub or Bitbucket."
        git remote -v
        return
    fi

    # Get default branch
    default_branch=$(git remote show origin | grep 'HEAD branch' | awk '{print $NF}')

    # Get current branch
    current_branch=$(parse_git_branch)
    pull_request_title="$current_branch -> $default_branch"

    # Get commit messages for each line in branch
    non_current_branches=$(git for-each-ref --format='%(refname)' refs/heads/ | grep -v "refs/heads/$current_branch")
    commit_messages=$(git log $current_branch --oneline --not $non_current_branches)
    readarray -t commit_messages <<< "$commit_messages"
    commit_message="Commits in pull request:\n"
    for message in "${commit_messages[@]}"; do
        commit_message+="\n$message"
    done
    repo_name=$(basename "$(git rev-parse --show-toplevel)")

    # Create PR content

    if [ $repo_home = "bitbucket" ]; then
        json_content="{
            \"title\": \"$pull_request_title\",
            \"description\": \"$commit_message\",
            \"source\": {
                \"branch\": {
                    \"name\": \"$current_branch\"
                }
            },
            \"destination\": {
                \"branch\": {
                    \"name\": \"$default_branch\"
                }
            }
        }"
        echo "$json_content" > temp_pr.json

        url="$BITBUCKET_BASE_URL/$repo_name/pull-requests"

        curl -X POST \
             -H "Authorization: Bearer $BITBUCKET_TOKEN" \
             -H "Content-Type: application/json" \
             -d @temp_pr.json \
             "$url"

    elif [ $repo_home = "github" ]; then
        json_content="{
            \"title\": \"$pull_request_title\",
            \"body\": \"$commit_message\",
            \"head\": \"$current_branch\",
            \"base\": \"$default_branch\"
        }"
        echo "$json_content" > temp_pr.json

        url="https://api.github.com/repos/$GITHUB_USERNAME/$repo_name/pulls"

        curl -X POST -H "Authorization: Bearer $GITHUB_TOKEN" \
            -H "Accept: application/vnd.github.v3+json" \
            -d @temp_pr.json \
            "$url"

    fi

    rm -f temp_pr.json
}
