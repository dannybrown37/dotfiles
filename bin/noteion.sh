#!/bin/bash

# Notion API endpoint and token
NOTION_API_URL="https://api.notion.com/v1/pages"
NOTION_VERSION="2022-06-28"
PROJECTS_TABLE_ID="1709f04dc8b18065a9a6ffb4b5dbd292"
THEATER_TABLE_ID="84a6fc454d0749fa961b39e4309bd445"
BOOKS_TABLE_ID="1789f04dc8b180c6bed6c29bdb46c0d0"

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
        1)
            echo "You chose Fiction."
            break
            ;;
        2)
            echo "You chose Non-Fiction."
            break
            ;;
        *)
            echo "Invalid option. Please choose 1 or 2."
            ;;
        esac
    done

    # Use the selected category for further processing
    echo "Selected category: $category"

    local payload=$(
        cat <<EOF
{
    "parent": {"database_id": "$BOOKS_TABLE_ID"},
    "properties": {
        "Book Title": {
            "title": [
                {
                    "text": {
                        "content": "$title"
                    }
                }
            ]
        },
        "Author Last Name": {
            "rich_text": [
                {
                    "text": {
                        "content": "$author_last"
                    }
                }
            ]
        },
        "Author First Name": {
            "rich_text": [
                {
                    "text": {
                        "content": "$author_first"
                    }
                }
            ]
        },
        "Times Read": {
            "rich_text": [
                {
                    "text": {
                        "content": "1"
                    }
                }
            ]
        },
        "Age": {
            "rich_text": [
                {
                    "text": {
                        "content": "$age"
                    }
                }
            ]
        },
        "Recommendation": {
            "rich_text": [
                {
                    "text": {
                        "content": "$recommendation"
                    }
                }
            ]
        },
        "Category": {
            "select": {
                "name": "$category"
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
        echo "Successfully added entry: $title"
    else
        echo "Failed to add entry. Response: $response"
    fi
}
alias add_book="update_books_table"

update_theater_table() {
    notion_validate || return 1

    read -r -p "Show name: " show_name
    read -r -p "Date (YYYY-MM-DD): " show_date
    read -r -p "Theater name: " theater_name
    read -r -p "Theater city and state (e.g. New York, NY): " theater_city
    read -r -p "Level of show (e.g., Broadway, School): " theater_level
    read -r -p "Any notes about the show: " show_notes
    read -r -p "Notable attendees: " notable_attendees

    local payload=$(
        cat <<EOF
{
    "parent": {"database_id": "$THEATER_TABLE_ID"},
    "properties": {
        "Show Name": {
            "title": [
                {
                    "text": {
                        "content": "$show_name"
                    }
                }
            ]
        },
        "Date": {
            "rich_text": [
                {
                    "text": {
                        "content": "$show_date"
                    }
                }
            ]
        },
        "Theatre": {
            "select": {
                "name": "$theater_name"
            }

        },
        "Where": {
            "rich_text": [
                {
                    "text": {
                        "content": "$theater_city"
                    }
                }
            ]
        },
        "Level": {
            "select": {
                "name": "$theater_level"
            }
        },
        "Notes": {
            "rich_text": [
                {
                    "text": {
                        "content": "$show_notes"
                    }
                }
            ]
        },
        "Attendees": {
            "rich_text": [
                {
                    "text": {
                        "content": "$notable_attendees"
                    }
                }
            ]
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
alias add_theater="update_theater_table"

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
alias triage="noteion"

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
