from unittest.mock import patch, MagicMock

from project_manager.models import Goal, Tactic
from project_manager.ui import CancelAction
from project_manager.cli import goal_menu


class TestGoalMenuCtrlC:
    def _make_goal(self) -> Goal:
        return Goal(
            name='test',
            description='',
            start_date='2026-06-06T00:00:00',
            end_date='2026-08-29T00:00:00',
            tactics=[
                Tactic(description='Do thing', reminder_cadence='daily'),
            ],
        )

    @patch('project_manager.cli.fzf_on_a_list', side_effect=CancelAction)
    def test_ctrl_c_on_menu_exits_cleanly(self, mock_fzf):
        goal = self._make_goal()
        # Should not raise — just returns
        goal_menu(goal)

    @patch('project_manager.cli.pause')
    @patch('project_manager.cli.fzf_on_a_list')
    def test_ctrl_c_during_action_returns_to_menu(self, mock_fzf, mock_pause):
        goal = self._make_goal()
        # First call: select scorecard, second call: Ctrl-C exits menu
        mock_fzf.side_effect = [
            ' 4. Score     Weekly scorecard',
            CancelAction,
        ]
        with patch(
            'project_manager.cli.GOAL_ACTION_MAP',
            {'Weekly scorecard': MagicMock(side_effect=CancelAction)},
        ):
            goal_menu(goal)
        # Verify we looped back (fzf called twice: action + next menu)
        assert mock_fzf.call_count == 2
