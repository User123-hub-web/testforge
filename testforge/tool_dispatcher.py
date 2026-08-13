"""Tool dispatcher - routes agent actions to their implementations."""
import os
from .models import Action
from .guardrail import check as guardrail_check


class ToolDispatcher:
    """
    Dispatches agent actions to tool implementations.
    
    Each tool is registered as a callable that takes params and returns a result.
    """
    
    def __init__(self, workspace_dir: str = "."):
        self.workspace_dir = os.path.abspath(workspace_dir)
        self.tools = {}
        self._register_default_tools()
    
    def _register_default_tools(self):
        """Register built-in tools."""
        self.tools["write_file"] = self._write_file
        self.tools["read_file"] = self._read_file
        self.tools["run_tests"] = self._run_tests
    
    def register_tool(self, name: str, handler):
        """Register a custom tool."""
        self.tools[name] = handler
    
    def dispatch(self, action: Action):
        """
        Execute an action after guardrail check.
        
        Returns:
            The tool's result, or a dict with 'error' key if blocked.
        """
        # Guardrail check
        guard_result = guardrail_check(action, self.workspace_dir)
        if not guard_result.allowed:
            return {
                "error": "BLOCKED",
                "reason": guard_result.reason,
                "requires_approval": guard_result.requires_approval,
            }
        
        # Route to tool
        if action.tool not in self.tools:
            return {"error": "UNKNOWN_TOOL", "reason": f"未注册的工具: {action.tool}"}
        
        try:
            return self.tools[action.tool](action.params)
        except Exception as e:
            return {"error": "TOOL_ERROR", "reason": str(e)}
    
    def _resolve_path(self, path: str) -> str:
        """Resolve a path relative to the workspace directory."""
        if os.path.isabs(path):
            return path
        return os.path.join(self.workspace_dir, path)
    
    # === Built-in tool implementations ===
    
    def _write_file(self, params):
        path = params.get("path", "")
        content = params.get("content", "")
        
        # Resolve path relative to workspace
        abs_path = self._resolve_path(path)
        abs_path = os.path.abspath(abs_path)
        
        # Ensure path is within workspace
        abs_workspace = os.path.abspath(self.workspace_dir)
        if not abs_path.startswith(abs_workspace):
            return {"error": "PATH_OUTSIDE_WORKSPACE", "path": abs_path}
        
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        return {"success": True, "path": abs_path}
    
    def _read_file(self, params):
        path = params.get("path", "")
        abs_path = self._resolve_path(path)
        abs_path = os.path.abspath(abs_path)
        
        if not os.path.exists(abs_path):
            return {"error": "FILE_NOT_FOUND", "path": abs_path}
        
        with open(abs_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        return {"success": True, "content": content}
    
    def _run_tests(self, params):
        from .test_runner import run_tests
        test_path = params.get("test_path", "")
        timeout = params.get("timeout", 30)
        
        # Resolve test path relative to workspace
        abs_test_path = self._resolve_path(test_path)
        
        result = run_tests(abs_test_path, timeout=timeout)
        
        return {
            "success": True,
            "all_passed": result.all_passed,
            "summary": result.summary,
            "test_result": result,
        }