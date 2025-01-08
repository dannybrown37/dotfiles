#!/bin/bash

# Notion API endpoint and token
NOTION_API_URL="https://api.notion.com/v1/pages"
NOTION_VERSION="2022-06-28"
PROJECTS_TABLE_ID="1709f04dc8b18065a9a6ffb4b5dbd292"

notion_validate() {
    if [ -z "$NOTION_NOTES_TOKEN" ]; then
        echo "Error: NOTION_NOTES_TOKEN is not set"
        return 1
    fi
}

noteion() {

    notion_validate || return 1

    local header="$*"

    if [ -z "$header" ]; then
        read -r -p "Enter a header for the note: " header
    fi

    echo "Enter additional details in multiple lines (empty line to finish):"
    local note_content=""
    while IFS= read -r line; do
        [[ -z "$line" ]] && break
        note_content+="$line"$'\n'
    done
    note_content=$(echo -n "$note_content" | sed ':a;N;$!ba;s/\n/\\n/g') # escape newlines for JSON formatting

    local contexts=$(get_notion_contexts)
    local context=$(echo "$contexts" | fzf --prompt "Select a context for $header")

    local payload=$(
        cat <<EOF
{
    "parent": {"database_id": "$PROJECTS_TABLE_ID"},
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
        },
        "Context": {
            "multi_select": [
                {
                    "name": "$context"
                }
            ]
        },
        "Status": {
            "select": {
                "name": "Triage"
            }
        }
    }
}
EOF
    )

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

get_notion_contexts() {
    local url="https://api.notion.com/v1/databases/${PROJECTS_TABLE_ID}/query"
    local response=$(curl -s -X POST "$url" \
          -H "Authorization: Bearer ${NOTION_NOTES_TOKEN}" \
          -H "Content-Type: application/json" \
          -H "Notion-Version: 2022-06-28")

    local contexts=$(echo "$response" | jq -r '.results[].properties.Context.multi_select[].name' | sort | uniq | grep -v "Pending Context")
    local final_contexts="Pending Context"$'\n'"$contexts"
    echo "$final_contexts"
}

trash_notion_page() {
    # not currently used but maybe useful in the future
    local page_id=$1
    local table_id=$2

    local url="${NOTION_API_URL}/${page_id//-/}"
    local delete_response=$(curl -s "$url" \
        -X PATCH \
        --data '{"in_trash": true}' \
        -H "Authorization: Bearer $NOTION_NOTES_TOKEN" \
        -H "Content-Type: application/json" \
        -H "Notion-Version: $NOTION_VERSION")

    if echo "$delete_response" | grep -q '"id":'; then
        echo "Synced table ID $table_id"
    else
        echo "Failed to delete page. Response: $delete_response"
    fi
}
