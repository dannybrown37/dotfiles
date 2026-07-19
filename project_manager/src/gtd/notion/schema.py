"""GTD Notion database schema definition — single source of truth."""

STATUSES = [
    'Triage',
    'Current Project',
    'Recurring',
    'Waiting For',
    'Someday/Maybe',
    'List',
]

STATUS_ICONS = {
    'Current Project': '🟢',
    'Recurring': '🔄',
    'Triage': '🟣',
    'Waiting For': '🔵',
    'Someday/Maybe': '💭',
    'List': '📋',
}

DEFAULT_CONTEXTS = [
    'Home',
    'Work',
    'Computer',
    'Errands',
    'Phone',
    '12-Week Goal',
]

DEFAULT_LIST_CATEGORIES = [
    'Weekend Trips to Take',
    'Fun Things to Do with Elliott',
    'Restaurants to Try',
    'Recipes to Try',
    'Books to Read',
    'Watchlist',
    'Websites to Surf',
    'Software to Try',
    'Musicals to See',
    'Bands to See',
    'Theatre',
    'Travel',
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
    'List Category': {
        'select': {
            'options': [{'name': c} for c in DEFAULT_LIST_CATEGORIES],
        },
    },
    'Next Actionable Step': {
        'rich_text': {},
    },
    'Success Condition': {
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
