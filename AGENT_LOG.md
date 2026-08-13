# AGENT_LOG.md — 实现过程日志

##  项目初始化
- **触发技能**：无（手动创建项目结构）
- **执行内容**：创建项目目录、`pyproject.toml`、`Makefile`、`.gitignore`
- **人工干预**：确认依赖列表（click、pytest），移除不必要的依赖

##  核心数据模型（T2）
- **触发技能**：无（手动编写）
- **执行内容**：定义 `Action`、`GuardrailResult`、`TestResult`、`FailureClassification` 等数据类
- **人工干预**：选择 `dataclasses` 而非 `pydantic`，减少外部依赖

##  Mock LLM 客户端（T3）
- **触发技能**：test-driven-development
- **执行内容**：先写测试（验证脚本顺序返回、调用计数、脚本耗尽异常），再实现 `MockLLM`
- **关键代码**：`llm.py` 中 `MockLLM.complete()` 方法
- **测试结果**：3 个测试全部通过

##  治理护栏（T7）
- **触发技能**：test-driven-development
- **执行内容**：先写 6 个护栏测试（危险命令、路径穿越、敏感路径、确定性），再实现 `guardrail.py`
- **关键决策**：`run_command` 一律需要审批，不是只拦截危险模式
- **人工干预**：添加 `DANGEROUS_PATTERNS` 列表时，手动补充了 fork bomb 模式

##  反馈校验器（T6，重点维度）
- **触发技能**：test-driven-development
- **执行内容**：先写 6 个分类测试，再实现 `classify()` 和 `format_feedback()`
- **关键决策**：分类顺序很重要（SyntaxError → ImportError → AssertionError → Timeout → 其他）
- **人工干预**：修正了 ImportError 和 ModuleNotFoundError 的匹配顺序

##  Agent 主循环（T11）
- **触发技能**：test-driven-development
- **执行内容**：先写 4 个集成测试（成功路径、失败反馈、最大轮数、解析错误），再实现 `agent_loop.py`
- **遇到问题**：`write_file` 和 `run_tests` 的路径解析不一致，导致文件写入位置错误
- **修复**：在 `ToolDispatcher` 中统一使用 `_resolve_path()` 方法，所有相对路径相对于 workspace_dir 解析
- **人工干预**：发现 guardrail 和 dispatcher 的路径解析逻辑重复，手动统一

##  机制演示（T13）
- **触发技能**：test-driven-development
- **执行内容**：编写 3 个演示测试，覆盖课程要求的三个机制演示
- **测试结果**：3 个演示测试全部通过

##  调试与修复
- **问题 1**：`test_feedback_received_after_failure` 失败，反馈索引错误
  - **原因**：断言检查 `messages_history[1]`，但反馈实际在 `messages_history[2]`
  - **修复**：将索引从 1 改为 2
- **问题 2**：guardrail 对相对路径的判断错误
  - **原因**：`os.path.abspath()` 相对当前工作目录而非 workspace_dir
  - **修复**：在 guardrail 中与 dispatcher 使用相同的路径解析逻辑
- **最终结果**：19/19 测试全部通过

## 学到的教训

1. **路径解析必须在所有模块间一致**：guardrail 和 dispatcher 各自解析路径导致 bug，应该集中到一个工具函数。
2. **测试断言必须精确**：`messages_history[1]` vs `messages_history[2]` 的差异导致了假失败。
3. **先写测试确实有效**：当 Mock LLM 脚本对不上时，测试立刻暴露了问题。
4. **Windows 和 Unix 的路径差异**：在 Windows 上开发时，`os.path.abspath()` 的行为与 Unix 略有不同。