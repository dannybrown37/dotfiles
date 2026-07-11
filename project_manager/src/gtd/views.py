import contextlib
from datetime import datetime
import subprocess


__all__ = ['detailed_view', 'view_goal']

from gtd.models import Goal, TOTAL_WEEKS
from gtd.ui import score_indicator, score_pct


def _tactics_compact_lines(goal: Goal) -> list[str]:
    """Build compact tactics section (one line each)."""
    week = goal.current_week()
    if not goal.tactics:
        return ['\n  No tactics yet.']
    lines = [f'\n  Tactics ({len(goal.tactics)}):']
    for i, t in enumerate(goal.tactics, 1):
        wk_key = str(week)
        mark = (
            f'{t.weekly_scores[wk_key]}/10'
            if wk_key in t.weekly_scores
            else '—'
        )
        logs = f'  [{len(t.updates)} logs]' if t.updates else ''
        lines.append(
            f'  {i}. [{mark:>4}] '
            f'{t.description}  ({t.reminder_cadence}){logs}',
        )
    return lines


def _goal_header_lines(goal: Goal) -> list[str]:
    """Build the header section for goal display."""
    week = goal.current_week()
    weeks_left = goal.weeks_remaining()
    lines = [
        f'{"─" * 55}',
        f'  {goal.name}',
        f'  {goal.date_range_display()}',
        (
            f'  {goal.progress_bar()}  •  Week {week}'
            f'  •  {weeks_left} week{"s" if weeks_left != 1 else ""} left'
        ),
        f'  {goal.description}',
    ]
    ex, tot = goal.overall_score()
    if tot > 0:
        pct = score_pct(ex, tot)
        indicator = score_indicator(ex / tot)
        lines.append(
            f'\n  {indicator} Overall execution: {pct} ({ex}/{tot})',
        )
    ex_w, tot_w = goal.week_score(week)
    if tot_w > 0:
        lines.append(
            f'  Week {week} score: {score_pct(ex_w, tot_w)} ({ex_w}/{tot_w})',
        )
    return lines


def _tactics_detail_lines(goal: Goal) -> list[str]:
    """Build detailed tactics section with all logs."""
    week = goal.current_week()
    if not goal.tactics:
        return ['\n  No tactics yet.']
    lines = [f'\n  Tactics ({len(goal.tactics)}):']
    for i, t in enumerate(goal.tactics, 1):
        wk_key = str(week)
        mark = (
            f'{t.weekly_scores[wk_key]}/10'
            if wk_key in t.weekly_scores
            else '—'
        )
        lines.append(
            f'\n  {i}. [{mark:>4}] {t.description}  ({t.reminder_cadence})',
        )
        if t.updates:
            lines.append(f'     Updates ({len(t.updates)}):')
            for u in t.updates:
                date = datetime.fromisoformat(
                    u.date,
                ).strftime('%b %-d')
                lines.append(f'       {date}: {u.note}')
    return lines


def _score_history_lines(goal: Goal) -> list[str]:
    """Build score history section."""
    week = goal.current_week()
    lines = ['\n  Score History:']
    for w in range(1, min(week, TOTAL_WEEKS) + 1):
        e, t = goal.week_score(w)
        if t == 0:
            lines.append(f'  Week {w:>2}: (not scored)')
        else:
            pct_val = e / t
            indicator = score_indicator(pct_val)
            current = ' ◀' if w == week else ''
            lines.append(
                f'  Week {w:>2}: {indicator} '
                f'{score_pct(e, t):>4} ({e}/{t}){current}',
            )
    return lines


def view_goal(goal: Goal) -> Goal:
    """Compact view -- fits on one screen."""
    lines = _goal_header_lines(goal)
    lines.extend(_tactics_compact_lines(goal))
    lines.append(f'{"─" * 55}\n')
    print('\n' + '\n'.join(lines))
    return goal


def detailed_view(goal: Goal) -> Goal:
    """Full detail piped through less."""
    lines = _goal_header_lines(goal)
    lines.extend(_tactics_detail_lines(goal))
    lines.extend(_score_history_lines(goal))
    lines.append(f'{"─" * 55}')

    output = '\n'.join(lines)
    with contextlib.suppress(KeyboardInterrupt):
        subprocess.run(
            ['/usr/bin/less', '-R'],
            input=output,
            text=True,
            check=False,
        )
    return goal
