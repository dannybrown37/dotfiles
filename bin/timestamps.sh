function epoch_timestamp() {  # @doc Print the current epoch timestamp in milliseconds, copy to clipboard
    echo $(($(date +%s%N) / 1000000)) | cb
}
alias epoch='epoch_timestamp'  # @doc Alias for epoch_timestamp

function utc_timestamp() {  # @doc Print the current UTC timestamp in ISO format with microseconds, copy to clipboard
    date -u +"%Y-%m-%dT%H:%M:%S.%3NZ" | cb
}
alias utc='utc_timestamp'  # @doc Alias for utc_timestamp
