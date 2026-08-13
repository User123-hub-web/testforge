"""Feedback validator - deterministic classification of test failures."""
from .models import TestResult, FailureClassification


def classify(test_result: TestResult) -> FailureClassification:
    """
    Classify a test result into a failure category.
    
    This is a pure function - deterministic and testable without any LLM.
    """
    if test_result.all_passed:
        return FailureClassification(
            category="ALL_PASSED",
            details="所有测试用例通过",
        )

    # Find the first failing test
    failing_tests = [tc for tc in test_result.test_cases if tc.status != "passed"]
    failed_names = [tc.name for tc in failing_tests]

    if not failing_tests:
        return FailureClassification(
            category="RUNTIME_ERROR",
            details="测试执行失败，但无法解析具体测试用例",
            failed_tests=failed_names,
        )

    first_failure = failing_tests[0]
    error_msg = first_failure.error_message or ""

    # Classify based on error message patterns
    if "SyntaxError" in error_msg or "IndentationError" in error_msg:
        category = "SYNTAX_ERROR"
        details = f"测试代码存在语法错误: {error_msg}"
    elif "ModuleNotFoundError" in error_msg or "ImportError" in error_msg:
        category = "IMPORT_ERROR"
        details = f"测试代码导入错误: {error_msg}"
    elif "AssertionError" in error_msg or first_failure.status == "failed":
        category = "ASSERTION_FAILURE"
        details = f"断言失败: {error_msg}"
    elif "Timeout" in error_msg or "timed out" in error_msg:
        category = "TIMEOUT"
        details = f"测试执行超时: {error_msg}"
    else:
        category = "RUNTIME_ERROR"
        details = f"运行时错误: {error_msg}"

    return FailureClassification(
        category=category,
        details=details,
        failed_tests=failed_names,
    )


def format_feedback(classification: FailureClassification) -> str:
    """Format a classification into a feedback message for the LLM."""
    if classification.category == "ALL_PASSED":
        return "✓ 所有测试通过。任务完成。"

    feedback = f"✗ 测试失败\n"
    feedback += f"失败类别: {classification.category}\n"
    feedback += f"详情: {classification.details}\n"
    if classification.failed_tests:
        feedback += f"失败的测试: {', '.join(classification.failed_tests)}\n"
    feedback += "\n请修正测试代码并重新运行。"
    return feedback