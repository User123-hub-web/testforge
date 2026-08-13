"""Core data models for TestForge harness."""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class FunctionInfo:
    """Metadata about a parsed Python function."""
    name: str
    args: List[str] = field(default_factory=list)
    return_annotation: Optional[str] = None
    docstring: Optional[str] = None
    source_code: str = ""
    file_path: str = ""


@dataclass
class Action:
    """An action the agent wants to execute."""
    tool: str
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GuardrailResult:
    """Result of a guardrail check."""
    allowed: bool
    reason: str = ""
    requires_approval: bool = False


@dataclass
class TestCaseResult:
    """Result of a single test case."""
    name: str
    status: str  # "passed" | "failed" | "error"
    error_message: Optional[str] = None


@dataclass
class TestResult:
    """Result of running a test suite."""
    test_cases: List[TestCaseResult] = field(default_factory=list)
    summary: Dict[str, int] = field(default_factory=dict)
    raw_output: str = ""

    @property
    def all_passed(self) -> bool:
        return len(self.test_cases) > 0 and all(
            tc.status == "passed" for tc in self.test_cases
        )


@dataclass
class FailureClassification:
    """Classification of a test failure."""
    category: str  # "SYNTAX_ERROR" | "IMPORT_ERROR" | "ASSERTION_FAILURE" | "RUNTIME_ERROR" | "TIMEOUT" | "ALL_PASSED"
    details: str = ""
    failed_tests: List[str] = field(default_factory=list)


@dataclass
class IterationRecord:
    """Record of one agent loop iteration."""
    round: int
    llm_response: str = ""
    actions: List[Action] = field(default_factory=list)
    test_result: Optional[TestResult] = None
    classification: Optional[FailureClassification] = None