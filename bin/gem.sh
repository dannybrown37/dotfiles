#!/usr/bin/env bash

function ask_gemini_a_question {
    if [ -z "$GOOGLE_API_KEY" ]; then
        echo "Please set the GOOGLE_API_KEY environment variable."
        return 1
    fi
    result=$(curl -s https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key="${GOOGLE_API_KEY}" \
        -H 'Content-Type: application/json' \
        -d "{
                \"contents\": [{
                    \"parts\": [
                        {\"text\": \"$*\"}
                    ]
                }]
            }" |
                jq -r '.candidates[0].content.parts[0].text')
    less -F <<< "$result"
}

alias gem='ask_gemini_a_question'


lgtm_prompt='Give me a pithy, brief, witty, and ridiculous way to say Looks Good To Me,
with a matching acronym on the line above. Such as AGFMP for Appears Groovy From My Perspective.
But not literally Looks Good To Me, that is not what I am looking for. That said, an alternative
LGTM acronym would be good, like Lightly Greased Turbo Machine or such. Make it plaintext, do not
include any formatting characters like asterisks. Do it on two lines, with the acronym first and
the expanded version second. Make sure the acronym matches the phrase. One of my favorites you
have come up with FLAGOAG Fits Like a Glove on a Giraffe, which is hilarious. The importance of
the phrase having the general meaning of "This is good, I approve this work" is paramount, please
keep on theme. Thank you ever so much for your service, you are a real one.'

alias lgtm='ask_gemini_a_question "${lgtm_prompt}"'
