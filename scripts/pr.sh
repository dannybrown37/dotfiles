#! bin/bash/


# Opens a pull request from current branch to default branch in repo
# Works with GitHub and enterprise Bitbucket

# To install, update your PATH in your .bashrc file, then source it:
#   export PATH="$HOME/path/to/script_dir:$PATH"
#   source ~/.bashrc

# To use, enter your BITBUCKET_TOKEN and BITBUCKET_BASE_URL in your
# environment, then just enter `pr` after pushing a branch up.


pr() {

    if git remote -v | grep -q "bitbucket"; then
        repo_home="bitbucket"
        if [[ -z $BITBUCKET_TOKEN || -z $BITBUCKET_BASE_URL ]]; then
            echo "Error: You must set your BITBUCKET_TOKEN and BITBUCKET_BASE_URL in the environment"
            echo "Hint: The base URL should end with \".com\", the rest will be constructed in-script"
            return
        fi
    elif git remote -v | grep -q "github"; then
        repo_home="github"
        if [[ -z $GITHUB_TOKEN ]]; then
            echo "Error: You must set your GITHUB_TOKEN in the environment"
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
    current_branch=$(git branch | sed -e '/^[^*]/d' -e 's/* \(.*\)/\1/')
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
    repo_parent=$(git remote -v | grep push | cut -d'/' -f4)

    # Create PR content

    if [ $repo_home = "bitbucket" ]; then

        json_content="{
            \"title\": \"$pull_request_title\",
            \"description\": \"$commit_message\",
            \"fromRef\": {
                \"id\": \"refs/heads/$current_branch\",
                \"repository\": \"$repo_name\",
                \"project\": {\"key\": \"$repo_parent\"}
            },
            \"toRef\": {
                \"id\": \"refs/heads/$default_branch\",
                \"repository\": \"$repo_name\",
                \"project\": {\"key\": \"$repo_parent\"}
            }
        }"
        echo "$json_content" > temp_pr.json

        url="$BITBUCKET_BASE_URL/rest/api/1.0/projects/$repo_parent/repos/$repo_name/pull-requests"
        data_type_header="Content-Type: application/json"
        token=$BITBUCKET_TOKEN

    elif [ $repo_home = "github" ]; then

        json_content="{
            \"title\": \"$pull_request_title\",
            \"body\": \"$commit_message\",
            \"head\": \"$current_branch\",
            \"base\": \"$default_branch\"
        }"
        echo "$json_content" > temp_pr.json

        url="https://api.github.com/repos/$repo_parent/$repo_name/pulls"
        data_type_header="Accept: application/vnd.github.v3+json"
        token=$GITHUB_TOKEN

    fi

    curl -X POST \
         -H "Authorization: Bearer $token" \
         -H "$data_type_header" \
         -d @temp_pr.json \
         "$url"

    rm -f temp_pr.json
}
