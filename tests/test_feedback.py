"""Unit tests for the feedback validator - deterministic classification."""
from testforge.models import TestResult, TestCaseResult
from testforge.feedback import classify, format_feedback


class TestFeedbackValidator:
    """Test that test failures are correctly classified."""

    def test_classifies_all_passed(self):
        """All tests passing should be classified as ALL_PASSED."""
        result = TestResult(
            test_cases=[
                TestCaseResult(name="test_a", status="passed"),
                TestCaseResult(name="test_b", status="passed"),
            ],
            summary={"total": 2, "passed": 2, "failed": 0, "errors": 0},
        )
        classification = classify(result)
        assert classification.category == "ALL_PASSED"

    def test_classifies_syntax_error(self):
        """SyntaxError in test code should be classified as SYNTAX_ERROR."""
        result = TestResult(
            test_cases=[
                TestCaseResult(
                    name="test_broken",
                    status="error",
                    error_message="SyntaxError: invalid syntax at line 3",
                ),
            ],
            summary={"total": 1, "passed": 0, "failed": 0, "errors": 1},
        )
        classification = classify(result)
        assert classification.category == "SYNTAX_ERROR"

    def test_classifies_import_error(self):
        """ModuleNotFoundError should be classified as IMPORT_ERROR."""
        result = TestResult(
            test_cases=[
                TestCaseResult(
                    name="test_missing_module",
                    status="error",
                    error_message="ModuleNotFoundError: No module named 'nonexistent'",
                ),
            ],
            summary={"total": 1, "passed": 0, "failed": 0, "errors": 1},
        )
        classification = classify(result)
        assert classification.category == "IMPORT_ERROR"

    def test_classifies_assertion_failure(self):
        """Failed assertions should be classified as ASSERTION_FAILURE."""
        result = TestResult(
            test_cases=[
                TestCaseResult(
                    name="test_wrong_value",
                    status="failed",
                    error_message="AssertionError: 2 != 3",
                ),
            ],
            summary={"total": 1, "passed": 0, "failed": 1, "errors": 0},
        )
        classification = classify(result)
        assert classification.category == "ASSERTION_FAILURE"

    def test_deterministic(self):
        """Same input must produce same classification."""
        result = TestResult(
            test_cases=[
                TestCaseResult(name="test_x", status="failed", error_message="AssertionError"),
            ],
            summary={"total": 1, "passed": 0, "failed": 1, "errors": 0},
        )
        c1 = classify(result)
        c2 = classify(result)
        assert c1.category == c2.category
        assert c1.details == c2.details

    def test_format_feedback_contains_key_info(self):
        """Formatted feedback should contain category, details, and failed tests."""
        classification = classify(
            TestResult(
                test_cases=[
                    TestCaseResult(
                        name="test_math",
                        status="failed",
                        error_message="AssertionError: expected 2, got 3",
                    ),
                ],
                summary={"total": 1, "passed": 0, "failed": 1, "errors": 0},
            )
        )
        feedback = format_feedback(classification)
        assert "ASSERTION_FAILURE" in feedback
        assert "test_math" in feedback