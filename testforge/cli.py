"""Command-line interface for TestForge."""
import click
from .llm import MockLLM
from .tool_dispatcher import ToolDispatcher
from .agent_loop import AgentLoop


@click.group()
def main():
    """TestForge - 测试生成与自修正 Coding Agent Harness."""
    pass


@main.command()
@click.argument("file_path")
@click.option("--function", "-f", default=None, help="只测试指定函数")
@click.option("--max-iterations", "-n", default=5, help="最大修正轮数")
@click.option("--verbose", "-v", is_flag=True, help="显示详细日志")
def generate(file_path, function, max_iterations, verbose):
    """
    为 Python 文件中的函数生成测试用例。
    
    FILE_PATH: 要测试的 Python 文件路径。
    """
    click.echo(f"[TestForge] 正在分析文件: {file_path}")
    click.echo(f"[TestForge] 最大迭代轮数: {max_iterations}")
    
    if function:
        click.echo(f"[TestForge] 目标函数: {function}")
    
    click.echo("\n[TestForge] 提示: 完整实现请安装 OpenAI API key 后使用真实 LLM。")
    click.echo("[TestForge] 当前使用 Mock LLM 演示核心闭环机制。\n")
    
    # Mock demo: show the harness loop works
    mock_script = [
        '{"tool": "write_file", "params": {"path": "test_generated.py", "content": "def test_dummy():\\n    assert 1 == 1\\n"}}',
        '{"tool": "run_tests", "params": {"test_path": "test_generated.py"}}',
    ]
    
    llm = MockLLM(script=mock_script)
    dispatcher = ToolDispatcher(workspace_dir=".")
    loop = AgentLoop(llm=llm, dispatcher=dispatcher, max_iterations=max_iterations)
    
    result = loop.run(initial_context=f"为 {file_path} 中的函数生成测试")
    
    click.echo(f"\n[TestForge] 运行结果: {result['status']}")
    click.echo(f"[TestForge] 迭代轮数: {result.get('iterations', 'N/A')}")
    
    if verbose:
        for record in result["history"]:
            click.echo(f"\n--- 第 {record.round} 轮 ---")
            click.echo(f"LLM 响应: {record.llm_response[:200]}")
            if record.classification:
                click.echo(f"失败分类: {record.classification.category}")


@main.command()
def credential():
    """管理 API 凭据（安全存储）。"""
    click.echo("[TestForge] 凭据管理功能")
    click.echo("[TestForge] 完整实现使用 keyring 库存储 API key 到系统钥匙串。")
    click.echo("[TestForge] 当前版本为演示模式，不存储真实凭据。")


if __name__ == "__main__":
    main()