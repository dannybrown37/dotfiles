from datetime import datetime, timedelta

from pydantic import BaseModel, Field


TOTAL_WEEKS = 12
SCORE_GREEN_THRESHOLD = 0.85
SCORE_YELLOW_THRESHOLD = 0.65


class Update(BaseModel):
    date: str  # ISO format
    note: str


class Tactic(BaseModel):
    description: str
    reminder_cadence: str  # e.g. "daily", "weekly", "2x/week"
    updates: list[Update] = Field(default_factory=list)
    weekly_scores: dict[str, int] = Field(
        default_factory=dict,
    )  # week number (str) -> 1-10 score


class Todo(BaseModel):
    description: str
    due_date: str | None = None
    completed: bool = False
    created_at: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
    )


class Goal(BaseModel):
    name: str
    description: str
    start_date: str
    end_date: str
    tactics: list[Tactic] = Field(default_factory=list)
    todos: list[Todo] = Field(default_factory=list)

    @classmethod
    def new(cls, name: str, description: str) -> 'Goal':
        now = datetime.now()
        return cls(
            name=name,
            description=description,
            start_date=now.isoformat(),
            end_date=(now + timedelta(weeks=12)).isoformat(),
        )

    @property
    def is_complete(self) -> bool:
        start = datetime.fromisoformat(self.start_date)
        return (datetime.now() - start).days >= TOTAL_WEEKS * 7

    def current_week(self) -> int:
        start = datetime.fromisoformat(self.start_date)
        elapsed = (datetime.now() - start).days // 7
        return min(max(elapsed + 1, 1), TOTAL_WEEKS)

    def weeks_remaining(self) -> int:
        return max(0, TOTAL_WEEKS - self.current_week())

    def week_start_date(self, week_num: int) -> datetime:
        start = datetime.fromisoformat(self.start_date)
        return start + timedelta(weeks=week_num - 1)

    def date_range_display(self) -> str:
        start = datetime.fromisoformat(self.start_date)
        end = datetime.fromisoformat(self.end_date)
        return f'{start:%b %-d} | {end:%b %-d, %Y}'

    def week_score(self, week_num: int) -> tuple[int, int]:
        """Returns (total_score, max_possible) for a given week."""
        total = 0
        max_possible = 0
        key = str(week_num)
        for t in self.tactics:
            if key in t.weekly_scores:
                max_possible += 10
                total += t.weekly_scores[key]
        return total, max_possible

    def overall_score(self) -> tuple[int, int]:
        """Returns (total_score, total_possible) across all scored weeks."""
        executed = 0
        total = 0
        for week in range(1, self.current_week() + 1):
            e, t = self.week_score(week)
            executed += e
            total += t
        return executed, total

    def progress_bar(self) -> str:
        week = self.current_week()
        if self.is_complete:
            filled = '█' * TOTAL_WEEKS
            return f'[{filled}] Complete'
        completed = max(0, week - 1)
        filled = '█' * completed
        empty = '░' * (TOTAL_WEEKS - completed)
        return f'[{filled}{empty}] Week {week}/{TOTAL_WEEKS}'
