"""Unit tests for the guardrail module - deterministic, no LLM needed."""
import pytest
from testforge.models import Action
from testforge.guardrail import check


class TestGuardrail:
    """Test that the guardrail deterministically blocks dangerous actions."""

    def test_blocks_dangerous_rm_rf(self):
        """A dangerous rm -rf / command must be blocked."""
        action = Action(tool="run_command", params={"command": "rm -rf /"})
        result = check(action)
        assert result.allowed is False
        assert "危险命令" in result.reason

    def test_blocks_all_run_commands(self):
        """All run_command actions require approval."""
        action = Action(tool="run_command", params={"command": "ls -la"})
        result = check(action)
        assert result.allowed is False
        assert result.requires_approval is True

    def test_allows_write_file_in_workspace(self):
        """Writing inside the workspace should be allowed."""
        action = Action(
            tool="write_file",
            params={"path": "./test_output.py", "content": "print('hello')"},
        )
        result = check(action, workspace_dir=".")
        assert result.allowed is True

    def test_blocks_write_outside_workspace(self):
        """Writing outside the workspace must be blocked."""
        action = Action(
            tool="write_file",
            params={"path": "/etc/passwd", "content": "malicious"},
        )
        result = check(action, workspace_dir=".")
        assert result.allowed is False
        assert "超出工作目录" in result.reason

    def test_blocks_sensitive_path(self):
        """Access to .env or other sensitive files must be blocked."""
        action = Action(tool="read_file", params={"path": ".env"})
        result = check(action, workspace_dir=".")
        assert result.allowed is False
        assert "敏感路径" in result.reason

    def test_deterministic(self):
        """Same input must always produce same output."""
        action = Action(tool="run_command", params={"command": "rm -rf /"})
        result1 = check(action)
        result2 = check(action)
        assert result1.allowed == result2.allowed
        assert result1.reason == result2.reason