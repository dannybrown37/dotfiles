function push() {  # @doc Push a message to ntfy.sh at $PERSONAL_ALERT_TOPIC | push <message>
    curl -fsS -d "$*" ntfy.sh/"${PERSONAL_ALERT_TOPIC}" >/dev/null
}

function push_to_topic() {  # @doc Push a message to ntfy.sh at a topic | push_to_topic <topic> <message>
    local topic=$1
    shift
    local message=$*

    curl -fsS -d "${message}" ntfy.sh/"${topic}" >/dev/null
}
