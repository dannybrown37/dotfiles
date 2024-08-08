#!/usr/bin/env bash

timestamp=$(date '+%Y-%m-%d %H:%M:%S')

export PATH="$HOME/.nvm/versions/node/v18.15.0/bin:$PATH"

~/.nvm/versions/node/v18.15.0/bin/aws-azure-login --no-prompt --all-profiles 2>&1 | while read line; do
    echo "$timestamp $line"
done >> "$HOME/cron_logs/aws-azure-login.output"
