"""Integration tests for the agent loop with Mock LLM."""
from testforge.llm import MockLLM
from testforge.tool_dispatcher import ToolDispatcher
from testforge.agent_loop import AgentLoop
import os
import tempfile


class TestAgentLoop:
    """Test the agent loop's core behaviors with a deterministic Mock LLM."""

    def test_success_on_all_pass_script(self):
        """When Mock LLM returns valid actions, the loop should succeed."""
        # Script: write a test file, then run tests that pass
        script = [
            '{"tool": "write_file", "params": {"path": "test_dummy.py", "content": "def test_ok():\\n    assert 1 == 1\\n"}}',
            '{"tool": "run_tests", "params": {"test_path": "test_dummy.py"}}',
        ]
        
        with tempfile.TemporaryDirectory() as tmpdir:
            llm = MockLLM(script=script)
            dispatcher = ToolDispatcher(workspace_dir=tmpdir)
            loop = AgentLoop(llm=llm, dispatcher=dispatcher, max_iterations=3)
            
            result = loop.run(initial_context="Generate tests")
            
            assert result["status"] == "SUCCESS"
            assert result["iterations"] <= 3
            assert llm.call_count == 2

    def test_feedback_received_after_failure(self):
        """When a test fails, the feedback should be passed back to the LLM."""
        # Script: write a failing test, run it (fails), then write a passing test, run again (passes)
        script = [
            '{"tool": "write_file", "params": {"path": "test_x.py", "content": "def test_fail():\\n    assert 1 == 2\\n"}}',
            '{"tool": "run_tests", "params": {"test_path": "test_x.py"}}',
            '{"tool": "write_file", "params": {"path": "test_x.py", "content": "def test_pass():\\n    assert 1 == 1\\n"}}',
            '{"tool": "run_tests", "params": {"test_path": "test_x.py"}}',
        ]
        
        with tempfile.TemporaryDirectory() as tmpdir:
            llm = MockLLM(script=script)
            dispatcher = ToolDispatcher(workspace_dir=tmpdir)
            loop = AgentLoop(llm=llm, dispatcher=dispatcher, max_iterations=5)
            
            result = loop.run(initial_context="Generate tests")
            
            assert result["status"] == "SUCCESS"
            # The third LLM call (index 2) should have received feedback about the failure
            assert "测试结果反馈" in llm.messages_history[2][-1]["content"]
            assert "ASSERTION_FAILURE" in llm.messages_history[2][-1]["content"]

    def test_max_iterations_reached(self):
        """When the LLM never produces passing tests, the loop should stop."""
        script = [
            '{"tool": "write_file", "params": {"path": "test_bad.py", "content": "def test_bad():\\n    assert 1 == 2\\n"}}',
            '{"tool": "run_tests", "params": {"test_path": "test_bad.py"}}',
        ] * 6  # Repeat to ensure script doesn't run out
        
        with tempfile.TemporaryDirectory() as tmpdir:
            llm = MockLLM(script=script)
            dispatcher = ToolDispatcher(workspace_dir=tmpdir)
            loop = AgentLoop(llm=llm, dispatcher=dispatcher, max_iterations=3)
            
            result = loop.run(initial_context="Generate tests")
            
            assert result["status"] == "MAX_ITERATIONS_REACHED"
            assert result["iterations"] == 3

    def test_unparseable_response_feedback(self):
        """Unparseable LLM responses should be fed back as errors."""
        script = [
            "I don't know what to do...",  # Not valid JSON
            '{"tool": "write_file", "params": {"path": "test_ok.py", "content": "def test_ok():\\n    assert True\\n"}}',
            '{"tool": "run_tests", "params": {"test_path": "test_ok.py"}}',
        ]
        
        with tempfile.TemporaryDirectory() as tmpdir:
            llm = MockLLM(script=script)
            dispatcher = ToolDispatcher(workspace_dir=tmpdir)
            loop = AgentLoop(llm=llm, dispatcher=dispatcher, max_iterations=5)
            
            result = loop.run(initial_context="Generate tests")
            
            assert result["status"] == "SUCCESS"
            # Second call should contain feedback about unparseable response
            assert "无法解析" in llm.messages_history[1][-1]["content"]