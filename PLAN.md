PLAN.md — TestForge 实现计划
每个 task 颗粒度控制在单个 subagent 一次会话内可完成（约 2–5 分钟人工介入，实际执行由 subagent 自主推进）。
所有任务强制 TDD：先编写失败测试并确认红色，再实现使其变绿，最后重构。
1. 计划总览
本项目共 16 个任务，划分为 5 个阶段：
阶段      任务   内容             依赖关系     可并行性
Phase 0   T1    项目脚手架与CI基础 无          串行起点
Phase 1   T2    核心数据模型与接口定义 T1      串行（为后续所有模块提供基础）
Phase 2   T3–T10 各独立模块实现       T2      8 个模块可并行开发（建议多个 worktree）
Phase 3   T11–T13 主循环集成、CLI、机制演示 T3–T10 串行（依赖所有模块）
Phase 4   T14–T16 CI 完善、分发、文档 T11–T13  可部分并行
2. 详细任务列表
Phase 0 — 基础
T1. 项目脚手架与 CI 基础
• 目标：创建项目目录结构、pyproject.toml、.gitignore、基础 CI 配置（GitHub Actions + GitLab CI），确保空测试可运行。
• 涉及文件：
◦ pyproject.toml（含项目元数据、依赖列表）
◦ .gitignore（排除 .env、__pycache__、*.pyc、.pytest_cache 等）
◦ .github/workflows/ci.yml（定义 unit-test job，运行 pytest）
◦ .gitlab-ci.yml（同 CI 配置）
◦ tests/ 目录（包含一个占位测试）
◦ Makefile（定义 test 命令）
• 预期实现要点：
◦ 使用 setuptools 或 hatch 作为构建后端。
◦ 依赖：click, pytest, keyring, openai（或抽象后可选）。
◦ CI 在 push 时自动运行 make test。
• 验证步骤：
1. 创建空测试文件 tests/test_dummy.py，运行 pytest 确认通过。
2. 本地运行 make test，确认输出正常。
3. 推送后 GitHub Actions 显示 pass。
• TDD 要求：本任务为基础设施，不涉及业务逻辑，跳过红绿循环。
￼
Phase 1 — 接口与数据模型
T2. 核心数据模型与接口定义
• 目标：定义项目中所有核心数据类（Action, GuardrailResult, TestResult, FailureClassification 等）和抽象接口（LLMClient, Tool, MemoryManager 等）。
• 涉及文件：
◦ testforge/core/models.py：所有数据类
◦ testforge/core/interfaces.py：抽象基类 / Protocol
• 预期实现要点：
◦ 严格对齐 SPEC §6 数据模型。
◦ 使用 dataclasses 或 pydantic（建议 dataclasses 减少依赖）。
◦ LLMClient 接口定义 complete(messages: List[Dict]) -> str。
◦ Tool 接口定义 execute(params: Dict) -> Any。
• 验证步骤：
1. 导入模块，确认所有类可实例化。
2. 使用 mypy（可选）检查类型。
• TDD 要求：本任务主要定义结构，可编写一个简单测试验证数据类字段默认值，先红后绿。
￼
Phase 2 — 独立模块并行开发
以下 T3–T10 为并行任务。
T3. Mock LLM 客户端
• 目标：实现 MockLLM 类，按照预设脚本返回响应，支持错误注入和调用计数。
• 涉及文件：testforge/llm/mock_client.py
• 预期实现要点：
◦ 实现 LLMClient 接口。
◦ 构造函数接收 script: List[LLMResponse]，每次调用返回下一条。
◦ 支持在脚本中指定返回内容或抛出异常（模拟 API 错误）。
• 验证步骤：
1. 先编写测试：传入脚本，验证返回序列正确、调用计数增加、脚本耗尽抛异常。
2. 运行测试确认失败（红），实现后通过（绿）。
T4. 输入解析模块
• 目标：解析 Python 文件，提取函数签名、docstring、源码片段，生成 FunctionInfo 列表。
• 涉及文件：testforge/parser/function_parser.py
• 预期实现要点：
◦ 使用 ast 标准库遍历函数定义。
◦ 支持 --function 过滤。
◦ 处理文件不存在、语法错误等情况。
• 验证步骤：
1. 编写 fixture 文件（含多个函数和装饰器）。
2. 测试解析结果数量、字段正确性。
3. 测试不存在的文件返回错误。
4. 先红后绿。
T5. 测试执行器
• 目标：在隔离子进程中运行 pytest，捕获输出并解析为 TestResult 结构化数据。
• 涉及文件：testforge/tools/test_runner.py
• 预期实现要点：
◦ 使用 subprocess.run 执行 pytest -q --json-report（或直接解析 stdout）。
◦ 设置超时（默认 30 秒），超时后终止子进程。
◦ 环境变量白名单，禁用网络。
• 验证步骤：
1. 创建临时目录和测试文件，调用执行器，验证返回的 TestResult 结构正确。
2. 测试超时场景（使用 sleep 测试）。
3. 先红后绿。
T6. 反馈校验器（核心）
• 目标：实现 FeedbackValidator，将 TestResult 分类为失败类型，并生成格式化的反馈消息。
• 涉及文件：testforge/core/feedback.py
• 预期实现要点：
◦ 纯函数 classify(test_result: TestResult) -> FailureClassification。
◦ 支持 SPEC §3.2.5 中所有分类。
◦ 生成反馈消息包含具体错误、失败测试名、相关代码行。
• 验证步骤：
1. 构造各类型 TestResult，验证分类结果。
2. 验证同一输入多次调用结果一致（确定性）。
3. 先红后绿。
T7. 治理护栏
• 目标：实现 Guardrail 类，检查 Action 是否允许，拦截危险操作。
• 涉及文件：testforge/core/guardrail.py
• 预期实现要点：
◦ 纯函数 check(action) -> GuardrailResult。
◦ 规则：禁止 rm -rf / 等危险命令、路径穿越检测、敏感路径访问、网络访问等。
• 验证步骤：
1. 构造危险 Action（如 run_command("rm -rf /")），断言拦截。
2. 正常 Action 允许通过。
3. 先红后绿。
T8. 工具分发
• 目标：实现 ToolDispatcher，根据 Action.tool 路由到对应工具处理函数，并返回结果。
• 涉及文件：testforge/core/tool_dispatcher.py, testforge/tools/file_tools.py
• 预期实现要点：
◦ 注册机制：将工具名映射到处理函数。
◦ 处理 write_file（限制工作目录内）、read_file、run_command（需经过护栏）。
◦ 未注册工具返回明确错误。
• 验证步骤：
1. 使用 mock 工具函数注册，测试分发正确。
2. 测试未注册工具报错。
3. 先红后绿。
T9. 记忆管理
• 目标：实现 MemoryManager，管理迭代记录，支持获取最近 N 条完整记录和更早摘要。
• 涉及文件：testforge/memory/manager.py
• 预期实现要点：
◦ 存储 IterationRecord 列表。
◦ get_recent(n) 返回最近 n 条。
◦ get_context(max_tokens) 返回适合 LLM 的上下文（截断策略）。
◦ 可选持久化到文件。
• 验证步骤：
1. 添加多条记录，验证获取最近记录的顺序和数量。
2. 验证 token 截断逻辑。
3. 先红后绿。
T10. 凭据管理
• 目标：实现 CredentialManager，使用 keyring 安全存储 API key，提供查看状态、设置、清除功能。
• 涉及文件：testforge/credentials/manager.py
• 预期实现要点：
◦ 封装 keyring 的 get_password, set_password, delete_password。
◦ 状态查看不回显明文，仅显示前缀。
◦ 首次录入使用隐藏输入。
• 验证步骤：
1. 使用 mock keyring 测试存储、读取、删除。
2. 验证状态输出不含完整 key。
3. 先红后绿。
￼
Phase 3 — 集成与演示
T11. Agent 主循环
• 目标：实现 AgentLoop 类，整合所有模块，实现完整闭环（组织上下文 → 调用 LLM → 解析动作 → 分发 → 回灌反馈 → 停机判断）。
• 涉及文件：testforge/core/agent_loop.py
• 预期实现要点：
◦ 构造函数注入 LLMClient, ToolDispatcher, Guardrail, FeedbackValidator, MemoryManager。
◦ 实现 run(initial_context) -> RunResult。
◦ 停机条件：全部通过、达到最大轮数、用户中止、连续解析失败。
◦ 解析 LLM 响应为 Action（JSON 格式或特定标记），解析失败作为反馈回灌。
• 验证步骤：
1. 使用 MockLLM 编写集成测试：模拟一次生成成功、一次失败后修正、一次达到最大轮数。
2. 验证反馈回灌（MockLLM 收到包含失败信息的消息）。
3. 验证停机条件。
4. 先红后绿。
T12. CLI 集成
• 目标：实现命令行入口，提供 generate 和 credential 子命令，整合 AgentLoop 和凭据管理。
• 涉及文件：testforge/cli.py, testforge/__main__.py
• 预期实现要点：
◦ 使用 click 定义命令。
◦ generate 接受文件路径、--function、--max-iterations、--verbose。
◦ 首次运行无凭据时引导录入。
◦ 输出进度和最终报告。
• 验证步骤：
1. 使用 click.testing.CliRunner 测试命令参数解析。
2. 模拟环境变量或 mock keyring，测试完整流程。
3. 先红后绿。
T13. 机制演示
• 目标：编写确定性演示脚本/测试，展示①治理护栏拦截危险动作；②注入失败后反馈闭环使 agent 改变下一步动作；③重点维度（反馈闭环）的确定性行为。
• 涉及文件：tests/demo/test_mechanism_demo.py 或 examples/mechanism_demo.py
• 预期实现要点：
◦ 演示 1：调用 Guardrail.check(Action(run_command("rm -rf /")))，输出拦截。
◦ 演示 2：MockLLM 脚本模拟第一轮生成错误测试，第二轮基于反馈修正，验证 AgentLoop 收到反馈并改变动作。
◦ 演示 3：展示 FeedbackValidator 对特定失败类型的分类。
• 验证步骤：
1. 运行演示，检查输出包含预期关键信息。
2. 作为测试可重复运行，通过断言验证。
￼
Phase 4 — 分发、CI 与文档
T14. CI 完善与离线测试
• 目标：完善 CI 配置，确保所有单元测试（含 mock LLM 测试）在无真实 LLM 环境下运行；添加 pytest --offline 标记。
• 涉及文件：.github/workflows/ci.yml, .gitlab-ci.yml, Makefile, pyproject.toml
• 预期实现要点：
◦ 配置 unit-test job，运行 make test-offline（只运行标记为 offline 的测试）。
◦ 使用 pytest 标记 @pytest.mark.offline 标注无需网络的测试。
• 验证步骤：
1. 本地运行 make test-offline 全部通过。
2. CI 执行成功。
T15. 分发准备（Docker + PyPI 打包）
• 目标：编写 Dockerfile，配置 PyPI 打包元数据，确保可通过 Docker 和 pip 安装运行。
• 涉及文件：Dockerfile, pyproject.toml, MANIFEST.in
• 预期实现要点：
◦ Dockerfile 基于 python:3.11-slim，安装项目并暴露 CLI 入口。
◦ 构建脚本验证镜像可运行 testforge --help。
◦ pyproject.toml 包含完整的项目描述和依赖。
• 验证步骤：
1. 本地构建 Docker 镜像，运行 docker run --rm testforge --help 输出帮助。
2. 使用 pip install -e . 后运行 testforge --help 成功。
T16. 文档与最终清理
• 目标：完善 README.md（包含简介、安装、运行、分发命令、目录结构、安全边界说明），更新 AGENT_LOG.md，确保所有交付物齐全。
• 涉及文件：README.md, AGENT_LOG.md, SPEC_PROCESS.md, REFLECTION.md（后两者由人工撰写，本任务仅确保文件存在）
• 预期实现要点：
◦ README 包含通用要求 §4.10 和 §五清单中的所有章节。
◦ 检查仓库无真实凭据。
• 验证步骤：
1. 逐项核对交付物清单。
2. 运行 git grep 搜索常见 key 模式（如 sk-）确保无泄露。

3. 依赖关系与并行策略

T1 → T2 → {T3, T4, T5, T6, T7, T8, T9, T10} → T11 → {T12, T13} → {T14, T15} → T16

• T3–T10 可并行：建议创建 8 个 worktree，每个模块一个 PR。每个 worktree 从主分支（已包含 T1、T2 的代码）创建。
• T12 与 T13 可并行：CLI 集成与机制演示无相互依赖，但均依赖 T11。
• T14 与 T15 可并行：CI 完善与分发准备独立。
4. Worktree / PR 计划
PR 编号 对应任务 内容 基础分支
PR #1 T1, T2 脚手架 + 接口定义 main
PR #2 T3 Mock LLM main（包含 T2 后）
PR #3 T4 输入解析 main（包含 T2 后）
PR #4 T5 测试执行器 main（包含 T2 后）
PR #5 T6 反馈校验器 main（包含 T2 后）
PR #6 T7 治理护栏 main（包含 T2 后）
PR #7 T8 工具分发 main（包含 T2 后）
PR #8 T9 记忆管理 main（包含 T2 后）
PR #9 T10 凭据管理 main（包含 T2 后）
PR #10 T11 主循环集成 main（合并 PR #2–#9 后）
PR #11 T12 CLI 集成  main（合并 PR #10 后）
PR #12 T13 机制演示 main（合并 PR #10 后）
PR #13 T14 CI 完善 main（合并 PR #11、#12 后）
PR #14 T15 分发准备 main（合并 PR #11、#12 后）
PR #15 T16 文档清理 main（合并 PR #13、#14 后）

5. 执行约定
• 每个 PR 合并前必须通过 CI：unit-test job 全绿。
• 每个任务完成后更新 PLAN.md：标记完成状态并附 commit hash。
• AGENT_LOG.md 记录每次 subagent 派发与人工干预。
• 两阶段评审：每个 PR 合并前，先进行 spec 合规检查（人工对照 SPEC），再进行代码质量检查（可借助编码智能体）。

