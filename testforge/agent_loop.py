"""Agent main loop - the core of the TestForge harness."""
import json
from typing import Optional
from .models import Action, IterationRecord, TestResult
from .llm import LLMClient
from .tool_dispatcher import ToolDispatcher
from .feedback import classify, format_feedback


class AgentLoop:
    """
    Main agent loop that orchestrates the generate-test-fix cycle.
    
    This is the core harness loop implemented from scratch:
    1. Build context
    2. Call LLM
    3. Parse action from response
    4. Dispatch action through tools
    5. Collect feedback
    6. Decide whether to stop or continue
    """
    
    def __init__(
        self,
        llm: LLMClient,
        dispatcher: ToolDispatcher,
        max_iterations: int = 5,
    ):
        self.llm = llm
        self.dispatcher = dispatcher
        self.max_iterations = max_iterations
        self.history: list[IterationRecord] = []
    
    def run(self, initial_context: str) -> dict:
        """
        Run the agent loop until a stop condition is met.
        
        Returns:
            A dict with run status, history, and final result.
        """
        context = initial_context
        
        for round_num in range(1, self.max_iterations + 1):
            record = IterationRecord(round=round_num)
            
            # Step 1: Call LLM with current context
            messages = [
                {"role": "system", "content": self._build_system_prompt()},
                {"role": "user", "content": context},
            ]
            
            try:
                llm_response = self.llm.complete(messages)
            except StopIteration:
                return {"status": "LLM_SCRIPT_EXHAUSTED", "history": self.history}
            except Exception as e:
                return {"status": "LLM_ERROR", "error": str(e), "history": self.history}
            
            record.llm_response = llm_response
            
            # Step 2: Parse action from LLM response
            action = self._parse_action(llm_response)
            if action is None:
                # Feedback: response was not parseable
                context += f"\n\n[系统反馈] 无法解析你的响应为有效动作。请以JSON格式输出动作。\n你的响应: {llm_response[:200]}"
                self.history.append(record)
                continue
            
            record.actions.append(action)
            
            # Step 3: Dispatch action
            result = self.dispatcher.dispatch(action)
            
            # Step 4: Collect feedback
            if "error" in result:
                context += f"\n\n[系统反馈] 动作执行失败: {result}"
                self.history.append(record)
                continue
            
            # If action was run_tests, classify the result
            if action.tool == "run_tests" and "test_result" in result:
                test_result = result["test_result"]
                record.test_result = test_result
                classification = classify(test_result)
                record.classification = classification
                
                feedback = format_feedback(classification)
                context += f"\n\n[测试结果反馈]\n{feedback}"
                
                # Step 5: Stop condition - all tests passed
                if classification.category == "ALL_PASSED":
                    self.history.append(record)
                    return {
                        "status": "SUCCESS",
                        "iterations": round_num,
                        "history": self.history,
                        "final_result": test_result,
                    }
            else:
                context += f"\n\n[动作结果] {json.dumps(result, ensure_ascii=False, default=str)[:500]}"
            
            self.history.append(record)
        
        # Reached max iterations
        return {
            "status": "MAX_ITERATIONS_REACHED",
            "iterations": self.max_iterations,
            "history": self.history,
        }
    
    def _build_system_prompt(self) -> str:
        return """你是一个测试生成 agent。你的任务是为给定的 Python 函数生成可运行的测试用例。

你可以执行以下动作（以 JSON 格式输出）：
1. {"tool": "write_file", "params": {"path": "test_xxx.py", "content": "测试代码"}}
2. {"tool": "run_tests", "params": {"test_path": "test_xxx.py"}}

如果测试失败，你会收到失败反馈，请修正测试代码后重新运行。
如果所有测试通过，任务完成。"""
    
    def _parse_action(self, llm_response: str) -> Optional[Action]:
        """Parse an action from the LLM response. Returns None if unparseable."""
        try:
            # Try to extract JSON from the response
            # Look for the first { and last }
            start = llm_response.find("{")
            end = llm_response.rfind("}")
            if start == -1 or end == -1:
                return None
            
            json_str = llm_response[start:end+1]
            data = json.loads(json_str)
            
            if "tool" not in data:
                return None
            
            return Action(
                tool=data["tool"],
                params=data.get("params", {}),
            )
        except (json.JSONDecodeError, KeyError, TypeError):
            return None