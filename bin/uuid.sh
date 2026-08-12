function generate_random_uuid_and_put_in_clipboard() {  # @doc Generate a random UUID and copy to clipboard
    uuid=$(cat /proc/sys/kernel/random/uuid)
    echo "$uuid" | cb
}
alias uuid='generate_random_uuid_and_put_in_clipboard'  # @doc Generate a random UUID and put it in the clipboard
