"""Habit and HabitCompletion dataclasses for Notion-backed tracking."""

from dataclasses import dataclass


@dataclass
class Habit:
    """Habit definition."""

    page_id: str
    name: str
    description: str = ''
    color: str = 'Blue'
    target_frequency: str = 'Daily'
    active: bool = True
    created_date: str = ''
    notes: str = ''

    @staticmethod
    def from_page(page: dict) -> 'Habit':
        """Parse Notion page into Habit dataclass."""
        props = page.get('properties', {})

        name = ''
        if title := props.get('Name', {}).get('title', []):
            name = title[0].get('plain_text', '')

        description = ''
        if rich := props.get('Description', {}).get('rich_text', []):
            description = rich[0].get('plain_text', '')

        color = 'Blue'
        if select := props.get('Color', {}).get('select', {}):
            color = select.get('name', 'Blue')

        target_frequency = 'Daily'
        if select := props.get('Target Frequency', {}).get('select', {}):
            target_frequency = select.get('name', 'Daily')

        active = props.get('Active', {}).get('checkbox', False)

        created_date = ''
        if date_obj := props.get('Created Date', {}).get('date', {}):
            created_date = date_obj.get('start', '')

        notes = ''
        if rich := props.get('Notes', {}).get('rich_text', []):
            notes = rich[0].get('plain_text', '')

        return Habit(
            page_id=page['id'].replace('-', ''),
            name=name,
            description=description,
            color=color,
            target_frequency=target_frequency,
            active=active,
            created_date=created_date,
            notes=notes,
        )


@dataclass
class HabitCompletion:
    """Single day completion record for a habit."""

    page_id: str
    habit_id: str
    date: str
    status: str
    notes: str = ''
    logged_at: str = ''

    @staticmethod
    def from_page(page: dict) -> 'HabitCompletion':
        """Parse Notion page into HabitCompletion dataclass."""
        props = page.get('properties', {})

        habit_id = ''
        if relation := props.get('Habit', {}).get('relation', []):
            habit_id = relation[0]['id'].replace('-', '')

        date = ''
        if date_obj := props.get('Date', {}).get('date', {}):
            date = date_obj.get('start', '')

        status = ''
        if select := props.get('Status', {}).get('select', {}):
            status = select.get('name', 'Incomplete')

        notes = ''
        if rich := props.get('Notes', {}).get('rich_text', []):
            notes = rich[0].get('plain_text', '')

        logged_at = page.get('created_time', '')

        return HabitCompletion(
            page_id=page['id'].replace('-', ''),
            habit_id=habit_id,
            date=date,
            status=status,
            notes=notes,
            logged_at=logged_at,
        )
