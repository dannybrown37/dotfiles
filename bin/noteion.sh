#!/bin/bash

# Notion API endpoint and token
NOTION_API_URL="https://api.notion.com/v1/pages"
NOTION_VERSION="2022-06-28"

notion_validate() {
    if [ -z "$NOTION_NOTES_TOKEN" ]; then
        echo "Error: NOTION_NOTES_TOKEN is not set"
        return 1
    fi
    if [ -z "$NOTION_NOTES_TABLE_ID" ]; then
        echo "Error: NOTION_NOTES_TABLE_ID is not set"
        return 1
    fi
}

noteions() {

    notion_validate || return 1

    # Send request to Notion API
    response=$(curl -s -X POST "$NOTION_API_URL/$NOTION_NOTES_TABLE_ID/query" \
        -H "Authorization: Bearer $NOTION_NOTES_TOKEN" \
        -H "Content-Type: application/json" \
        -H "Notion-Version: $NOTION_VERSION")

    echo $response

    # Check for errors
    if echo "$response" | grep -q '"object": "error"'; then
        echo "Failed to fetch data from Notion. Response: $response"
        return 1
    fi

    # Parse and display results
    echo "Database contents:"
    echo "$response" | jq '.results[] | {id: .id, properties: .properties}'
}

noteion() {

    notion_validate || return 1

    local header="$*"

    if [ -z "$header" ]; then
        read -r -p "Enter a header for the note: " header
    fi

    echo "Enter additional lines for file (empty input to finish):"
    local note_content=""
    while IFS= read -r line; do
        [[ -z "$line" ]] && break
        note_content+="$line"$'\n'
    done
    note_content=$(echo -n "$note_content" | sed ':a;N;$!ba;s/\n/\\n/g') # escape newlines for JSON formatting

    # Create JSON payload
    local payload=$(
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
        },
        "Created Date": {
            "date": {
                "start": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
            }
        }
    }
}
EOF
    )

    # Send request to Notion API
    local response=$(curl -s -X POST "$NOTION_API_URL" \
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
