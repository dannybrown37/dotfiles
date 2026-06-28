from unittest.mock import patch

from project_manager.views import detailed_view
from project_manager.models import Goal


class TestDetailedView:
    def _make_goal(self) -> Goal:
        return Goal(
            name='test',
            description='A test goal',
            start_date='2026-06-06T00:00:00',
            end_date='2026-08-29T00:00:00',
        )

    @patch('project_manager.views.subprocess.run')
    def test_returns_goal_on_normal_exit(self, mock_run):
        goal = self._make_goal()
        result = detailed_view(goal)
        assert result is goal
        mock_run.assert_called_once()

    @patch(
        'project_manager.views.subprocess.run', side_effect=KeyboardInterrupt
    )
    def test_ctrl_c_returns_goal_without_raising(self, mock_run):
        goal = self._make_goal()
        result = detailed_view(goal)
        assert result is goal
