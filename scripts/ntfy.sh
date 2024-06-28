#!/usr/bin/bash -i

##
## This requires the ntfy app on your phone.
## It will send a push alert to your phone if you subscribe to the
## topic within the app.
##

push_to_topic() {
    local topic=$1
    shift
    local message=$*

    http POST ntfy.sh/"${topic}" alert="${message}"
}

push() {
    topic="danny_is_alerted"
    http POST ntfy.sh/"${topic}" alert="$*"
}
