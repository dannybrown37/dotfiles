#!/usr/bin/env bash

# @doc Ask Gemini questions from the terminal (lazy-loaded on first use)

_load_gem() {
    unset -f _load_gem gem ask_gemini_a_question lgtm pokemon

    ask_gemini_a_question() {
        if [[ -z "$GOOGLE_API_KEY" ]]; then
            echo "Please set the GOOGLE_API_KEY environment variable."
            return 1
        fi
        local result
        result=$(curl -s \
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=${GOOGLE_API_KEY}" \
            -H 'Content-Type: application/json' \
            -d "{\"contents\": [{\"parts\": [{\"text\": \"$*\"}]}]}")
        jq -r '.candidates[0].content.parts[0].text' <<< "$result" | less -F
    }

    gem() { ask_gemini_a_question "$@"; }

    # Global (no 'local') so lgtm() and pokemon() can reference them after _load_gem returns
    _lgtm_prompt='Give me a pithy, brief, witty, and ridiculous way to say Looks Good To Me,
with a matching acronym on the line above. Such as AGFMP for Appears Groovy From My Perspective.
But not literally Looks Good To Me, that is not what I am looking for. That said, an alternative
LGTM acronym would be good, like Lightly Greased Turbo Machine or such. Make it plaintext, do not
include any formatting characters like asterisks. Do it on two lines, with the acronym first and
the expanded version second. Make sure the acronym matches the phrase. One of my favorites you
have come up with FLAGOAG Fits Like a Glove on a Giraffe, which is hilarious. The importance of
the phrase having the general meaning of This is good, I approve this work is paramount, please
keep on theme. Thank you ever so much for your service, you are a real one. If I provide a single
word after the colon, make the acronym that word. Otherwise follow the instructions after the colon,
if any:'
    _pokemon_prompt="${_lgtm_prompt} Choose a random number between 1 and 151 and make the acronym the corresponding pokemon!"

    lgtm()    { ask_gemini_a_question "${_lgtm_prompt} $1" | cowsay | lolcat | cb; }
    pokemon() { ask_gemini_a_question "${_pokemon_prompt}" | cb | cowsay | lolcat | cb; }
}

gem()                   { _load_gem; gem "$@"; }
ask_gemini_a_question() { _load_gem; ask_gemini_a_question "$@"; }
lgtm()                  { _load_gem; lgtm "$@"; }
pokemon()               { _load_gem; pokemon; }
