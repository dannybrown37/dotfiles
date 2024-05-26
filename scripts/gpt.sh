#!/bin/bash

function gpt() {
    CHATGPT_URL="https://chat.openai.com/"
    DEBUG_PORT=9222

    google-chrome --remote-debugging-port=$DEBUG_PORT &

    TABS_JSON=$(chrome-remote-interface list | sed -e "s/^'//" -e "s/'$//" | jq -r 'map(select(.type == "page") | {id: .id, title: .title})')

    echo $TABS_JSON

    if [ -z "$TAB_ID" ]; then
        google-chrome "$CHATGPT_URL" > /dev/null 2>&1 &
    else
        ACTIVATE_URL="http://localhost:$DEBUG_PORT/json/activate/$TAB_ID"
        curl -s "$ACTIVATE_URL" > /dev/null
        echo "Focused on the existing ChatGPT tab."
    fi
}
