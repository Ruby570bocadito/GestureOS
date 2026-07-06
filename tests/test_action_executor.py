"""Tests for HandsControl action executor."""

import pytest


class TestActionExecutor:
    """Tests that require pyautogui. Skipped if no display available."""

    @pytest.fixture(autouse=True)
    def _skip_if_no_display(self):
        try:
            from src.utils.action_executor import ActionExecutor  # noqa: F811
        except Exception:
            pytest.skip("no display available for pyautogui")

    def test_create(self):
        from src.utils.action_executor import ActionExecutor

        executor = ActionExecutor()
        assert executor is not None

    def test_create_with_callbacks(self):
        from src.utils.action_executor import ActionExecutor

        logs = []
        speaks = []

        def log_cb(msg):
            logs.append(msg)

        def speak_cb(msg):
            speaks.append(msg)

        executor = ActionExecutor(log_callback=log_cb, speak_callback=speak_cb)
        assert executor._log is not None
        assert executor._speak is not None

    def test_execute_unknown_action(self):
        from src.utils.action_executor import ActionExecutor

        executor = ActionExecutor()
        result = executor.execute("nonexistent_action", {})
        assert result is None
