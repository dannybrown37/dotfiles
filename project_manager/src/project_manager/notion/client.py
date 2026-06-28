import os
import sys

import httpx


NOTION_API_URL = 'https://api.notion.com/v1'
NOTION_VERSION = '2022-06-28'


def get_token() -> str:
    """Get Notion token from environment."""
    token = os.environ.get('NOTION_NOTES_TOKEN')
    if not token:
        print('Error: NOTION_NOTES_TOKEN is not set.')
        sys.exit(1)
    return token


def get_projects_db_id() -> str:
    """Get GTD Projects database ID from environment."""
    db_id = os.environ.get('NOTION_PROJECTS_DB_ID')
    if not db_id:
        print('Error: NOTION_PROJECTS_DB_ID is not set.')
        sys.exit(1)
    return db_id


def _headers() -> dict[str, str]:
    return {
        'Authorization': f'Bearer {get_token()}',
        'Content-Type': 'application/json',
        'Notion-Version': NOTION_VERSION,
    }


def query_database(
    *,
    database_id: str | None = None,
    filter_obj: dict | None = None,
    page_size: int = 100,
) -> list[dict]:
    """Query a Notion database and return all pages."""
    if database_id is None:
        database_id = get_projects_db_id()
    url = f'{NOTION_API_URL}/databases/{database_id}/query'
    payload: dict = {'page_size': page_size}
    if filter_obj:
        payload['filter'] = filter_obj

    all_results = []
    has_more = True
    while has_more:
        response = httpx.post(url, headers=_headers(), json=payload)
        response.raise_for_status()
        data = response.json()
        all_results.extend(data['results'])
        has_more = data.get('has_more', False)
        if has_more:
            payload['start_cursor'] = data['next_cursor']

    return all_results
