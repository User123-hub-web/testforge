"""
机制演示 - Mechanism Demonstration

按课程要求 (A.6) 提交的三个确定性演示：
1. 治理护栏拦截危险动作
2. 注入失败后反馈闭环使 agent 收到反馈并改变下一步动作
3. 重点维度（反馈闭环）的确定性行为
"""
import pytest
from testforge.models import Action
from testforge.guardrail import check
from testforge.llm import MockLLM
from testforge.tool_dispatcher import ToolDispatcher
from testforge.agent_loop import AgentLoop
from testforge.feedback import classify, format_feedback
from testforge.models import TestResult, TestCaseResult
import tempfile


class TestMechanismDemo:
    """Demonstrates the three required mechanisms deterministically."""

    def test_demo_1_guardrail_blocks_dangerous_action(self):
        """
        演示 1: 治理护栏拦截危险动作。
        
        The guardrail deterministically blocks `rm -rf /` without any LLM involvement.
        """
        action = Action(tool="run_command", params={"command": "rm -rf /"})
        result = check(action)
        
        assert result.allowed is False
        assert result.requires_approval is True
        assert "危险命令" in result.reason
        
        print(f"\n[演示1] 护栏拦截: {result.reason}")

    def test_demo_2_feedback_loop_changes_agent_behavior(self):
        """
        演示 2: 注入一次失败，反馈闭环使 agent 收到反馈并改变下一步动作。
        
        The MockLLM script simulates:
        - Round 1: Write a failing test (assertion error)
        - Round 2: Run it -> fails -> feedback injected
        - Round 3: Write a corrected test based on feedback
        - Round 4: Run it -> passes
        """
        script = [
            # Round 1: Write a test with wrong assertion
            '{"tool": "write_file", "params": {"path": "test_demo.py", "content": "def test_add():\\n    assert 1 + 1 == 3\\n"}}',
            # Round 2: Run the failing test
            '{"tool": "run_tests", "params": {"test_path": "test_demo.py"}}',
            # Round 3: Fix the assertion based on feedback
            '{"tool": "write_file", "params": {"path": "test_demo.py", "content": "def test_add():\\n    assert 1 + 1 == 2\\n"}}',
            # Round 4: Run the corrected test
            '{"tool": "run_tests", "params": {"test_path": "test_demo.py"}}',
        ]
        
        with tempfile.TemporaryDirectory() as tmpdir:
            llm = MockLLM(script=script)
            dispatcher = ToolDispatcher(workspace_dir=tmpdir)
            loop = AgentLoop(llm=llm, dispatcher=dispatcher, max_iterations=5)
            
            result = loop.run(initial_context="为 add 函数生成测试")
            
            # Assert the loop succeeded
            assert result["status"] == "SUCCESS"
            
            # Assert that the LLM received failure feedback before its third call
            third_call_messages = llm.messages_history[2]
            combined = " ".join(m["content"] for m in third_call_messages)
            assert "ASSERTION_FAILURE" in combined
            assert "测试结果反馈" in combined
            
            print(f"\n[演示2] 反馈闭环: agent 收到失败反馈后修正并最终通过")

    def test_demo_3_feedback_classification_deterministic(self):
        """
        演示 3: 重点维度（反馈闭环）的确定性行为。
        
        The FeedbackValidator must classify the same input identically every time.
        """
        test_result = TestResult(
            test_cases=[
                TestCaseResult(
                    name="test_broken",
                    status="failed",
                    error_message="AssertionError: expected 5, got 4",
                ),
            ],
            summary={"total": 1, "passed": 0, "failed": 1, "errors": 0},
        )
        
        # Classify 100 times - must always be identical
        classifications = [classify(test_result) for _ in range(100)]
        
        categories = {c.category for c in classifications}
        details = {c.details for c in classifications}
        
        assert len(categories) == 1
        assert "ASSERTION_FAILURE" in categories
        assert len(details) == 1
        
        feedback = format_feedback(classifications[0])
        assert "ASSERTION_FAILURE" in feedback
        assert "test_broken" in feedback
        
        print(f"\n[演示3] 反馈分类确定性: 100次分类结果完全一致 -> {classifications[0].category}")