function push() {  # @doc Push a message to ntfy.sh at $PERSONAL_ALERT_TOPIC | push <message>
    http POST ntfy.sh/"${PERSONAL_ALERT_TOPIC}" alert="$*"
}

function push_to_topic() {  # @doc Push a message to ntfy.sh at a topic | push_to_topic <topic> <message>
    local topic=$1
    shift
    local message=$*

    http POST ntfy.sh/"${topic}" alert="${message}"
}
