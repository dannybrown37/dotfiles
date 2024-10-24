#!/bin/bash

# Notion API endpoint and token
NOTION_API_URL="https://api.notion.com/v1/pages"
NOTION_VERSION="2022-06-28"

# Function to add an entry to a Notion database
noteion() {

    if [ -z "$NOTION_NOTES_TOKEN" ]; then
        echo "Error: noteionS_TOKEN is not set"
        return
    fi

    if [ -z "$NOTION_NOTES_TABLE_ID" ]; then
        echo "Error: NOTION_NOTES_TABLE_ID is not set"
        return
    fi

    local header="$*"

    if [ -z "$header" ]; then
        read -r -p "Enter the header of the note: " header
    fi

    echo "Enter additional lines for file (empty input to finish):"
    note_content=""
    while IFS= read -r line; do
        [[ -z "$line" ]] && break
        note_content+="$line"$'\n'
    done
    note_content=$(echo "$note_content" | sed ':a;N;$!ba;s/\n/\\n/g') # escape newlines for JSON formatting

    # Create JSON payload
    payload=$(
        cat <<EOF
{
    "parent": {"database_id": "$NOTION_NOTES_TABLE_ID"},
    "properties": {
        "Header": {
            "title": [
                {
                    "text": {
                        "content": "$header"
                    }
                }
            ]
        },
        "Details": {
            "rich_text": [
                {
                    "text": {
                        "content": "$note_content"
                    }
                }
            ]
        }
    }
}
EOF
    )

    # Send request to Notion API
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
