#!/bin/bash

# @doc Create Notion pages from the terminal (lazy-loaded on first use)

_load_noteion() {
    unset -f _load_noteion noteion triage add_book add_theater \
             update_books_table update_theater_table \
             get_notion_contexts trash_notion_page notion_validate

    NOTION_API_URL="https://api.notion.com/v1/pages"
    NOTION_VERSION="2022-06-28"
    PROJECTS_TABLE_ID="${NOTION_PROJECTS_DB_ID}"
    THEATER_TABLE_ID="${NOTION_THEATER_DB_ID}"
    BOOKS_TABLE_ID="${NOTION_BOOKS_DB_ID}"

    notion_validate() {
        if [ -z "$NOTION_NOTES_TOKEN" ]; then
            echo "Error: NOTION_NOTES_TOKEN is not set"
            return 1
        fi
    }

    update_books_table() {
        notion_validate || return 1

        read -r -p "Title: " title
        read -r -p "Author Last Name: " author_last
        read -r -p "Author First Name: " author_first
        read -r -p "Age Read: " age
        read -r -p "Recommendation: " recommendation
        echo "Choose a category:"
        select category in "Fiction" "Non-Fiction"; do
            case $REPLY in
            1) echo "You chose Fiction."; break ;;
            2) echo "You chose Non-Fiction."; break ;;
            *) echo "Invalid option. Please choose 1 or 2." ;;
            esac
        done

        local payload
        payload=$(cat <<EOF
{
    "parent": {"database_id": "$BOOKS_TABLE_ID"},
    "properties": {
        "Book Title": {"title": [{"text": {"content": "$title"}}]},
        "Author Last Name": {"rich_text": [{"text": {"content": "$author_last"}}]},
        "Author First Name": {"rich_text": [{"text": {"content": "$author_first"}}]},
        "Times Read": {"rich_text": [{"text": {"content": "1"}}]},
        "Age": {"rich_text": [{"text": {"content": "$age"}}]},
        "Recommendation": {"rich_text": [{"text": {"content": "$recommendation"}}]},
        "Category": {"select": {"name": "$category"}}
    }
}
EOF
)
        local response
        response=$(curl -s -X POST "$NOTION_API_URL" \
            -H "Authorization: Bearer $NOTION_NOTES_TOKEN" \
            -H "Content-Type: application/json" \
            -H "Notion-Version: $NOTION_VERSION" \
            -d "$payload")

        if echo "$response" | grep -q '"id":'; then
            echo "Successfully added entry: $title"
        else
            echo "Failed to add entry. Response: $response"
        fi
    }

    update_theater_table() {
        notion_validate || return 1

        read -r -p "Show name: " show_name
        read -r -p "Date (YYYY-MM-DD): " show_date
        read -r -p "Theater name: " theater_name
        read -r -p "Theater city and state (e.g. New York, NY): " theater_city
        read -r -p "Level of show (e.g., Broadway, School): " theater_level
        read -r -p "Any notes about the show: " show_notes
        read -r -p "Notable attendees: " notable_attendees

        local payload
        payload=$(cat <<EOF
{
    "parent": {"database_id": "$THEATER_TABLE_ID"},
    "properties": {
        "Show Name": {"title": [{"text": {"content": "$show_name"}}]},
        "Date": {"rich_text": [{"text": {"content": "$show_date"}}]},
        "Theatre": {"select": {"name": "$theater_name"}},
        "Where": {"rich_text": [{"text": {"content": "$theater_city"}}]},
        "Level": {"select": {"name": "$theater_level"}},
        "Notes": {"rich_text": [{"text": {"content": "$show_notes"}}]},
        "Attendees": {"rich_text": [{"text": {"content": "$notable_attendees"}}]}
    }
}
EOF
)
        local response
        response=$(curl -s -X POST "$NOTION_API_URL" \
            -H "Authorization: Bearer $NOTION_NOTES_TOKEN" \
            -H "Content-Type: application/json" \
            -H "Notion-Version: $NOTION_VERSION" \
            -d "$payload")

        if echo "$response" | grep -q '"id":'; then
            echo "Successfully added entry: $show_name"
        else
            echo "Failed to add entry. Response: $response"
        fi
    }

    get_notion_contexts() {
        local url="https://api.notion.com/v1/databases/${PROJECTS_TABLE_ID}/query"
        local response
        response=$(curl -s -X POST "$url" \
            -H "Authorization: Bearer $NOTION_NOTES_TOKEN" \
            -H "Content-Type: application/json" \
            -H "Notion-Version: 2022-06-28")
        local contexts
        contexts=$(echo "$response" | jq -r '.results[].properties.Context.multi_select[].name' | sort | uniq | grep -v "Pending Context")
        echo "Pending Context"$'\n'"$contexts"
    }

    noteion() {
        notion_validate || return 1

        local header="$*"
        if [[ -z "$header" ]]; then
            read -r -p "Enter a header for the note: " header
        fi

        echo "Enter additional details in multiple lines (empty line to finish):"
        local note_content=""
        while IFS= read -r line; do
            [[ -z "$line" ]] && break
            note_content+="$line"$'\n'
        done
        note_content=$(echo -n "$note_content" | sed ':a;N;$!ba;s/\n/\\n/g')

        local context
        context=$(get_notion_contexts | fzf --prompt "Select a context for $header")

        local payload
        payload=$(cat <<EOF
{
    "parent": {"database_id": "$PROJECTS_TABLE_ID"},
    "properties": {
        "Header": {"title": [{"text": {"content": "$header"}}]},
        "Details": {"rich_text": [{"text": {"content": "$note_content"}}]},
        "Created Date": {"date": {"start": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"}},
        "Context": {"multi_select": [{"name": "$context"}]},
        "Status": {"select": {"name": "Triage"}}
    }
}
EOF
)
        local response
        response=$(curl -s -X POST "$NOTION_API_URL" \
            -H "Authorization: Bearer $NOTION_NOTES_TOKEN" \
            -H "Content-Type: application/json" \
            -H "Notion-Version: $NOTION_VERSION" \
            -d "$payload")

        if echo "$response" | grep -q '"id":'; then
            echo "Successfully added entry: $header"
        else
            echo "Failed to add entry. Response: $response"
        fi
    }

    trash_notion_page() {
        local page_id=$1
        local url="${NOTION_API_URL}/${page_id//-/}"
        local delete_response
        delete_response=$(curl -s "$url" \
            -X PATCH \
            --data '{"in_trash": true}' \
            -H "Authorization: Bearer $NOTION_NOTES_TOKEN" \
            -H "Content-Type: application/json" \
            -H "Notion-Version: $NOTION_VERSION")

        if echo "$delete_response" | grep -q '"id":'; then
            echo "Trashed page $page_id"
        else
            echo "Failed to trash page. Response: $delete_response"
        fi
    }

    add_book()    { update_books_table "$@"; }
    add_theater() { update_theater_table "$@"; }
    triage()      { noteion "$@"; }
}

noteion()             { _load_noteion; noteion "$@"; }
triage()              { _load_noteion; triage "$@"; }
add_book()            { _load_noteion; add_book "$@"; }
add_theater()         { _load_noteion; add_theater "$@"; }
