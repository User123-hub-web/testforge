"""Test runner - executes pytest in a subprocess and parses results."""
import subprocess
import os
import sys
from .models import TestResult, TestCaseResult


def run_tests(test_file_path: str, timeout: int = 30) -> TestResult:
    """
    Run pytest on the given test file and parse the output.
    
    Args:
        test_file_path: Path to the test file to run.
        timeout: Maximum time in seconds before killing the test.
    
    Returns:
        TestResult with structured test case results.
    """
    test_file_path = os.path.abspath(test_file_path)
    workdir = os.path.dirname(test_file_path)
    
    # Use sys.executable to ensure we use the same Python interpreter
    python_exe = sys.executable
    
    # Build pytest command
    cmd = [
        python_exe, "-m", "pytest",
        test_file_path,
        "-v",
        "--tb=short",
        "--no-header",
        "--disable-warnings",
        "-p", "no:cacheprovider",
    ]
    
    # Set up isolated environment
    env = os.environ.copy()
    env["PYTEST_ADDOPTS"] = ""
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=workdir,
            env=env,
        )
        
        # Parse the verbose output to extract test results
        test_cases = _parse_pytest_output(proc.stdout + proc.stderr)
        
        # If no test cases were parsed, use exit code to determine result
        if not test_cases:
            if proc.returncode == 0:
                test_cases = [TestCaseResult(name="all_tests", status="passed")]
            else:
                # Include the actual error message
                error_detail = (proc.stderr or proc.stdout or "测试执行失败").strip()
                # Limit error message length
                if len(error_detail) > 500:
                    error_detail = error_detail[:500] + "..."
                test_cases = [
                    TestCaseResult(
                        name="test_execution",
                        status="error",
                        error_message=error_detail,
                    )
                ]
        
        total = len(test_cases)
        passed = sum(1 for tc in test_cases if tc.status == "passed")
        failed = sum(1 for tc in test_cases if tc.status == "failed")
        errors = sum(1 for tc in test_cases if tc.status == "error")
        
        return TestResult(
            test_cases=test_cases,
            summary={
                "total": total,
                "passed": passed,
                "failed": failed,
                "errors": errors,
            },
            raw_output=proc.stdout + proc.stderr,
        )
    
    except subprocess.TimeoutExpired:
        return TestResult(
            test_cases=[TestCaseResult(name="TIMEOUT", status="error", 
                                       error_message="测试执行超时")],
            summary={"total": 1, "passed": 0, "failed": 0, "errors": 1},
            raw_output="Timeout after {} seconds".format(timeout),
        )
    except Exception as e:
        return TestResult(
            test_cases=[TestCaseResult(name="EXECUTION_ERROR", status="error",
                                       error_message=str(e))],
            summary={"total": 1, "passed": 0, "failed": 0, "errors": 1},
            raw_output=str(e),
        )


def _parse_pytest_output(output: str):
    """Parse pytest verbose output to extract test case results."""
    test_cases = []
    lines = output.split("\n")
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Match patterns like "test_name PASSED" or "test_name FAILED"
        # pytest verbose output format: "test_file.py::test_name PASSED [xx%]"
        if " PASSED" in line:
            if "::" in line:
                name = line.split("::")[-1].split(" ")[0]
            else:
                name = line.split(" ")[0]
            test_cases.append(TestCaseResult(name=name, status="passed"))
        elif " FAILED" in line:
            if "::" in line:
                name = line.split("::")[-1].split(" ")[0]
            else:
                name = line.split(" ")[0]
            test_cases.append(TestCaseResult(name=name, status="failed",
                                             error_message="断言失败"))
        elif " ERROR" in line:
            if "::" in line:
                name = line.split("::")[-1].split(" ")[0]
            else:
                name = line.split(" ")[0]
            test_cases.append(TestCaseResult(name=name, status="error",
                                             error_message="测试执行错误"))
    
    return test_cases