"""LLM abstraction layer with mock implementation for offline testing."""
from typing import Dict, List


class LLMClient:
    """Abstract LLM client interface."""
    
    def complete(self, messages: List[Dict[str, str]]) -> str:
        raise NotImplementedError


class MockLLM(LLMClient):
    """
    Mock LLM that returns responses from a preset script.
    
    Used for deterministic unit testing of the harness without
    any network or real LLM dependency.
    """
    
    def __init__(self, script: List[str]):
        """
        Args:
            script: List of response strings. Each call to complete()
                    returns the next string in the list.
        """
        self.script = script
        self.call_count = 0
        self.messages_history: List[List[Dict[str, str]]] = []
    
    def complete(self, messages: List[Dict[str, str]]) -> str:
        """Return the next scripted response."""
        self.messages_history.append(messages)
        if self.call_count >= len(self.script):
            raise StopIteration("Mock LLM 脚本耗尽")
        response = self.script[self.call_count]
        self.call_count += 1
        return response