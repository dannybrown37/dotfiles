#!/bin/bash

# Notion API endpoint and token
NOTION_API_URL="https://api.notion.com/v1/pages"
NOTION_VERSION="2022-06-28"
PROJECTS_TABLE_ID="1709f04dc8b18065a9a6ffb4b5dbd292"
CONTEXTS_TABLE_ID="1709f04dc8b180daae50f821ac38d73e"

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

    echo "Enter additional lines for file (empty input to finish):"
    local note_content=""
    while IFS= read -r line; do
        [[ -z "$line" ]] && break
        note_content+="$line"$'\n'
    done
    note_content=$(echo -n "$note_content" | sed ':a;N;$!ba;s/\n/\\n/g') # escape newlines for JSON formatting

    local contexts=$(get_notion_contexts)
    local context=$(echo "$contexts" | fzf --prompt "Select a context for $header")

    # Create JSON payload
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

get_notion_contexts() {
    local url="https://api.notion.com/v1/databases/${CONTEXTS_TABLE_ID}/query"
    local response=$(curl -s -X POST "$url" \
        -H "Authorization: Bearer $NOTION_NOTES_TOKEN" \
        -H "Content-Type: application/json" \
        -H "Notion-Version: $NOTION_VERSION")

    echo "$response" | jq -r '.results[].properties.Name.title[].text.content' | sort
}

sync_notion_multi_selects_with_contexts_single_page() {
    local table_id=$1
    local contexts
    # Assuming get_notion_contexts is getting the contexts as expected
    IFS=$'\n' read -rd '' -a contexts <<< "$(get_notion_contexts)"

    # Prepare the context array in JSON format
    local context_json=""
    for context in "${contexts[@]}"; do
        context_json+="{\"name\": \"$context\"},"
    done
    # shellcheck disable=SC2001
    context_json=$(echo "$context_json" | sed 's/,$//')

    # Now build the JSON payload
    local payload=$(
        cat <<EOF
{
    "parent": {"database_id": "$table_id"},
    "properties": {
        "Header": {
            "title": [
                {
                    "text": {
                        "content": "Sync record"
                    }
                }
            ]
        },
        "Details": {
            "rich_text": [
                {
                    "text": {
                        "content": ""
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
            "multi_select": [$context_json]
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
        local page_id=$(echo "$response" | jq -r '.id')  # Extract page id
        trash_notion_page "$page_id" "$table_id"  # Call the delete function
    else
        echo "Failed to add entry. Response: $response"
    fi
}

trash_notion_page() {
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

sync_notion_multi_selects_with_contexts_all_pages() {
    sync_notion_multi_selects_with_contexts_single_page "$PROJECTS_TABLE_ID"
}

alias sync_notion="sync_notion_multi_selects_with_contexts_all_pages"
