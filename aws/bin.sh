#!/usr/bin/env bash

##
## Various utility functions using the AWS CLI
##


buildlogs() {  # latest build logs in CLI; required arg is AWS stage
    # shellcheck disable=SC2153
    [[ $# -eq 0 ]] && dev_stage="${DEV_STACK}" && echo "Using default stage ${DEV_STAGE}; pass an arg to override"
    [[ -z $BUILD_ARTIFACTS_BUCKET ]] && echo "BUILD_ARTIFACTS_BUCKET is not set" && return
    [[ $# -eq 1 ]] && dev_stage=$1
    conditional_aws_azure_login
    aws s3 cp "s3://${BUILD_ARTIFACTS_BUCKET}/${dev_stage}-back-end-build-logs/$(aws s3 ls "s3://${BUILD_ARTIFACTS_BUCKET}/${dev_stage}-back-end-build-logs/" | sort -n | tail -1 | awk '{ print $4 }' )" - | zcat -
}


conditional_aws_azure_login() {
    check_aws_credentials() {
        aws sts get-caller-identity > /dev/null 2>&1
        return $?
    }
    check_aws_credentials
    local exit_code=$?
    if [ $exit_code -ne 0 ]; then
        echo "AWS credentials are expired or invalid. Renewing credentials..."
        aws-azure-login -f --all-profiles --no-prompt
        check_aws_credentials
        if [ $? -eq 0 ]; then
            echo "AWS credentials successfully renewed."
        else
            echo "Failed to renew AWS credentials."
            exit 1
        fi
    else
        echo "AWS credentials are valid."
    fi
}


open_lambda_and_cloudwatch_logs_in_browser() {
    # open browser to particular Lambda's monitoring page
    # lopen arg1 [developer stage] [AWS region] [Lambda name]
    # env variables:
    # LAMBDA_PATHS -- an array of paths to search for Lambda folders
    # DEV_STACK -- the name of the dev stage
    if [[ $# -lt 3 ]]; then
        lambda_folder=$(find "${LAMBDA_PATHS[@]}" \
                        -mindepth 1 -maxdepth 1 \
                        -type d \
                        -not -path '*/node_modules*' \
                        | sed "s|^${HOME}/projects/||" \
                        | fzf)
        [[ -z "${lambda_folder}" ]] && echo "Error: No Lambda folder selected" && return
        lambda_name=$(basename "${lambda_folder}")
    fi
    if [[ $# -eq 0 ]]; then
        stage="${DEV_STACK}"
        if [[ -z "${stage}" ]]; then
            echo "Error: no DEV_STACK environment variable set or arg passed"
            exit 1
        fi
        echo "Using default stage ${DEV_STACK}; pass an arg to override"
        aws_region="us-east-1"
        echo "Using default region us-east-1; pass an arg to override"
    elif [[ $# -eq 1 ]]; then
        stage=$1
        aws_region="us-east-1"
        echo "Using default region us-east-1; pass an arg to override"
    elif [[ $# -eq 2 ]]; then
        stage=$1
        aws_region=$2
    elif [[ $# -eq 3 ]]; then
        stage=$1
        aws_region=$2
        lambda_name=$3
    else
        echo "Error: Invalid number of arguments"
        return
    fi

    stage_title_case=$(echo "${stage}" | awk '{print toupper(substr($0, 1, 1)) tolower(substr($0, 2))}')

    if [[ ! "${lambda_name,,}" == *"demo"* ]]; then
        lambda_name="${lambda_name}${stage_title_case}"
    fi

    lambda_name=${lambda_name/demo/$stage}
    lambda_name=${lambda_name/Demo/$stage_title_case}

    url="https://${aws_region}.console.aws.amazon.com/lambda/home?region=${aws_region}#/functions/${lambda_name}/?subtab=triggers&tab=configure"
    echo "$url"

    log_group_name=$(aws lambda get-function-configuration \
                    --function-name "$lambda_name" \
                    --query "LoggingConfig" \
                    --output json |
                        jq -r '.LogGroup')
    log_group_url="https://console.aws.amazon.com/cloudwatch/home#logStream:group=${log_group_name}"
    echo "$log_group_url"

    cmd.exe /c start "${url}" 2>/dev/null
    cmd.exe /c start "${log_group_url}" 2>/dev/null
}

alias caal='conditional_aws_azure_login'
alias lopen='open_lambda_and_cloudwatch_logs_in_browser'

complete -C '/usr/local/bin/aws_completer' aws
