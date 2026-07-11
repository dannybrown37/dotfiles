"""GTD Notion database schema definition — single source of truth."""

STATUSES = [
    'Triage',
    'Current Project',
    'Recurring',
    'Waiting For',
    'Someday/Maybe',
]

STATUS_ICONS = {
    'Current Project': '🟢',
    'Recurring': '🔄',
    'Triage': '🟣',
    'Waiting For': '🔵',
    'Someday/Maybe': '💭',
}

DEFAULT_CONTEXTS = [
    'Home',
    'Work',
    'Computer',
    'Errands',
    'Phone',
    '12-Week Goal',
]

DB_SCHEMA: dict = {
    'Header': {
        'title': {},
    },
    'Status': {
        'select': {
            'options': [{'name': s} for s in STATUSES],
        },
    },
    'Context': {
        'select': {
            'options': [{'name': c} for c in DEFAULT_CONTEXTS],
        },
    },
    'Next Actionable Step': {
        'rich_text': {},
    },
    'Intended Successful Outcome': {
        'rich_text': {},
    },
    'Due Date': {
        'date': {},
    },
    'Follow-Up Date': {
        'date': {},
    },
    'Created Date': {
        'date': {},
    },
}
