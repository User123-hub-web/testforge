# TestForge

一个 Coding Agent Harness：给定 Python 函数，自动生成测试用例，运行测试，并在失败时根据反馈自动修正。

## 项目简介

TestForge 是一个测试生成与自修正的编码智能体框架（harness）。它实现了完整的 agent 闭环：
输入 Python 文件 → 解析函数 → LLM 生成测试 → 运行测试 → 失败分类 → 反馈回灌 → 自动修正 → 全部通过

核心机制（主循环、工具分发、治理护栏、反馈校验器）全部由代码实现，可在 Mock LLM 下离线运行，所有核心行为都有确定性单元测试覆盖。

## 安装

```bash
git clone https://github.com/User123-hub-web/testforge.git
cd testforge
pip install -e .
要求：Python 3.11+
运行
# 生成测试（当前为 Mock LLM 演示模式）
testforge generate ./path/to/your/code.py

# 查看凭据状态
testforge credential
运行测试
make test
# 或
python -m pytest tests/ -v
分发命令
Docker
docker build -t testforge .
docker run --rm testforge --help
PyPI（本地打包）
pip install build
python -m build
目录结构
testforge/
├── testforge/              # 核心代码
│   ├── agent_loop.py       # Agent 主循环（自研）
│   ├── guardrail.py        # 治理护栏（自研，确定性）
│   ├── feedback.py         # 反馈校验器（自研，确定性）
│   ├── tool_dispatcher.py  # 工具分发（自研）
│   ├── test_runner.py      # 测试执行器
│   ├── llm.py              # LLM 抽象层 + Mock LLM
│   ├── models.py           # 核心数据模型
│   └── cli.py              # CLI 入口
├── tests/                  # 单元测试（19 个，全部离线可运行）
│   ├── test_guardrail.py
│   ├── test_feedback.py
│   ├── test_agent_loop.py
│   └── test_mechanism_demo.py
├── .github/workflows/ci.yml # CI 配置
├── Dockerfile
├── pyproject.toml
├── Makefile
├── SPEC.md
├── PLAN.md
├── SPEC_PROCESS.md
├── AGENT_LOG.md
└── REFLECTION.md
安全边界说明
API Key 安全配置
• 绝不在源码中硬编码 API Key
• 绝不提交 .env 到 Git（已在 .gitignore 中排除）
• 推荐使用系统钥匙串（通过 keyring 库）
• 不要通过命令行 export 设置 key（会进入 shell history）
• 当前版本为 Mock LLM 演示模式，不存储真实凭据。接入真实 LLM 时，请使用 testforge credential set 交互式录入。
治理护栏
以下行为会被确定性拦截（不依赖 LLM 判断）：
• 执行 rm -rf / 等危险 shell 命令
• 写入工作目录之外的文件
• 访问 .env、.ssh、.aws 等敏感路径
• 所有 run_command 操作需要人工审批
已知限制
• 当前版本使用 Mock LLM 演示闭环机制，未接入真实 LLM API
• 仅支持 Python 目标代码
• Windows 推荐使用 WSL2 运行
• 输入解析模块（function_parser.py）尚未在最小版本中实现，当前通过 CLI 参数传递目标文件路径
机制演示
运行以下命令查看三个核心机制的确定性演示：
python -m pytest tests/test_mechanism_demo.py -v -s
演示内容：
1. 治理护栏拦截危险动作：rm -rf / 被确定性拦截
2. 反馈闭环：注入失败 → agent 收到反馈 → 改变动作 → 最终通过
3. 反馈分类确定性：同一输入 100 次分类结果完全一致