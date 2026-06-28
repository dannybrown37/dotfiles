"""Parse Notion page properties into simple data structures."""

from dataclasses import dataclass


__all__ = ['ProjectEntry']


@dataclass
class ProjectEntry:
    """A single entry from the GTD Projects table."""

    page_id: str
    header: str
    status: str
    context: str
    details: str
    next_step: str
    due_date: str | None
    follow_up_date: str | None
    created_date: str

    @classmethod
    def from_page(cls, page: dict) -> 'ProjectEntry':
        props = page['properties']
        return cls(
            page_id=page['id'],
            header=_get_title(props.get('Header', {})),
            status=_get_select(props.get('Status', {})),
            context=_get_select(props.get('Context', {})),
            details=_get_rich_text(props.get('Details', {})),
            next_step=_get_rich_text(
                props.get('Next Actionable Step', {}),
            ),
            due_date=_get_date(props.get('Due Date', {})),
            follow_up_date=_get_date(props.get('Follow-Up Date', {})),
            created_date=page.get('created_time', ''),
        )

    @property
    def is_12_week_goal(self) -> bool:
        return self.context == '12-Week Goal'


def _get_title(prop: dict) -> str:
    title_list = prop.get('title', [])
    if not title_list:
        return ''
    return title_list[0].get('plain_text', '')


def _get_select(prop: dict) -> str:
    select = prop.get('select')
    if not select:
        return ''
    return select.get('name', '')


def _get_rich_text(prop: dict) -> str:
    texts = prop.get('rich_text', [])
    if not texts:
        return ''
    return ' '.join(t.get('plain_text', '') for t in texts).strip()


def _get_date(prop: dict) -> str | None:
    date = prop.get('date')
    if not date:
        return None
    return date.get('start')
