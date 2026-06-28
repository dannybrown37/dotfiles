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


def get_database_schema(
    *,
    database_id: str | None = None,
) -> dict:
    """Fetch database schema (properties and their options)."""
    if database_id is None:
        database_id = get_projects_db_id()
    url = f'{NOTION_API_URL}/databases/{database_id}'
    response = httpx.get(url, headers=_headers())
    response.raise_for_status()
    return response.json()


def get_select_options(property_name: str) -> list[str]:
    """Get available options for a select property."""
    schema = get_database_schema()
    prop = schema['properties'].get(property_name, {})
    options = prop.get('select', {}).get('options', [])
    return [o['name'] for o in options]


def update_page(page_id: str, properties: dict) -> dict:
    """Update a Notion page's properties."""
    url = f'{NOTION_API_URL}/pages/{page_id}'
    payload = {'properties': properties}
    response = httpx.patch(url, headers=_headers(), json=payload)
    response.raise_for_status()
    return response.json()


def get_page_body(page_id: str) -> str:
    """Fetch the text content from a page's body blocks."""
    url = f'{NOTION_API_URL}/blocks/{page_id}/children'
    response = httpx.get(url, headers=_headers())
    response.raise_for_status()
    blocks = response.json().get('results', [])
    lines = []
    for block in blocks:
        if block['type'] == 'paragraph':
            texts = block['paragraph']['rich_text']
            content = ' '.join(t['plain_text'] for t in texts).strip()
            if content:
                lines.append(content)
    return '\n'.join(lines)


def build_property_update(
    *,
    status: str | None = None,
    context: str | None = None,
    next_step: str | None = None,
    due_date: str | None = None,
    follow_up_date: str | None = None,
) -> dict:
    """Build a properties dict for a page update."""
    props: dict = {}
    if status is not None:
        props['Status'] = {'select': {'name': status}}
    if context is not None:
        props['Context'] = {'select': {'name': context}}
    if next_step is not None:
        props['Next Actionable Step'] = {
            'rich_text': [{'text': {'content': next_step}}],
        }
    if due_date is not None:
        if due_date == '':
            props['Due Date'] = {'date': None}
        else:
            props['Due Date'] = {'date': {'start': due_date}}
    if follow_up_date is not None:
        if follow_up_date == '':
            props['Follow-Up Date'] = {'date': None}
        else:
            props['Follow-Up Date'] = {'date': {'start': follow_up_date}}
    return props


def archive_page(page_id: str) -> dict:
    """Move a Notion page to trash."""
    url = f'{NOTION_API_URL}/pages/{page_id}'
    payload = {'in_trash': True}
    response = httpx.patch(url, headers=_headers(), json=payload)
    response.raise_for_status()
    return response.json()
