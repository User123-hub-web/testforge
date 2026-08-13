"""Governance guardrail - deterministic safety checks for agent actions."""
import os
from .models import Action, GuardrailResult

# Dangerous command patterns that must always be blocked
DANGEROUS_PATTERNS = [
    "rm -rf /",
    "rm -rf /*",
    "rm -rf ~",
    "mkfs",
    "dd if=",
    ":(){ :|:& };:",
    "shutdown",
    "reboot",
    "sudo rm",
]

# Sensitive paths that must never be read or written
SENSITIVE_PATHS = [
    ".env",
    ".ssh",
    ".aws",
    "credentials",
    ".git/config",
    "keychain",
]


def check(action: Action, workspace_dir: str = ".") -> GuardrailResult:
    """
    Deterministic guardrail check for an agent action.
    
    This is a pure function - it does not rely on any LLM.
    Given the same input, it always produces the same output.
    """
    tool = action.tool
    params = action.params

    # Check 1: run_command must always require approval
    if tool == "run_command":
        command = params.get("command", "")
        for pattern in DANGEROUS_PATTERNS:
            if pattern in command:
                return GuardrailResult(
                    allowed=False,
                    reason=f"危险命令被拦截: '{pattern}'",
                    requires_approval=True,
                )
        return GuardrailResult(
            allowed=False,
            reason="run_command 需要人工审批",
            requires_approval=True,
        )

    # Check 2: write_file must stay within workspace
    if tool == "write_file":
        path = params.get("path", "")
        abs_workspace = os.path.abspath(workspace_dir)
        
        # Resolve the path the same way ToolDispatcher does
        if os.path.isabs(path):
            abs_path = os.path.abspath(path)
        else:
            abs_path = os.path.abspath(os.path.join(workspace_dir, path))
        
        if not abs_path.startswith(abs_workspace):
            return GuardrailResult(
                allowed=False,
                reason=f"写入路径超出工作目录: {path}",
            )

    # Check 3: Block access to sensitive paths
    if tool in ("read_file", "write_file"):
        path = params.get("path", "")
        for sensitive in SENSITIVE_PATHS:
            if sensitive in path:
                return GuardrailResult(
                    allowed=False,
                    reason=f"禁止访问敏感路径: {path}",
                )

    # All checks passed
    return GuardrailResult(allowed=True)