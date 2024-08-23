#!/usr/bin/env bash

function ask_gemini_a_question() {
  if [ -z "$GOOGLE_API_KEY" ]; then
    echo "Please set the GOOGLE_API_KEY environment variable."
    return 1
  fi
  curl -s https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${GOOGLE_API_KEY} \
  -H 'Content-Type: application/json' \
  -d "{
    \"contents\": [{
      \"parts\": [
        {\"text\": \"$*\"}
      ]
    }]
  }" \
  | jq -r '.candidates[0].content.parts[0].text'
}

alias gem='ask_gemini_a_question'
