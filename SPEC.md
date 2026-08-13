# SPEC.md — TestForge: 测试生成与自修正 Coding Agent Harness

> 项目类型：A · Coding Agent Harness

---

## 1. 问题陈述

### 1.1 要解决的问题

软件测试是软件开发中最耗时、最容易被忽视的环节。开发者通常知道应该写测试，但在以下场景中往往力不从心：

- 接手陌生代码库时，不了解函数的行为和边界条件；
- 函数逻辑复杂，分支众多，手工枚举测试用例容易遗漏；
- 测试用例写出来后失败，需要反复调试测试代码本身（而非被测代码）才能通过；
- 被测代码本身存在 bug，导致测试失败，但开发者难以区分"测试写错了"和"代码有 bug"。

现有的 AI 辅助测试工具（如 Copilot 的测试生成）大多停留在"一次性生成测试"的层面：生成完就结束，不执行、不验证、不修正。生成的测试是否真的能运行、是否真的覆盖了边界条件、是否与被测代码的语义一致，全靠开发者自己判断。

### 1.2 目标用户

- **软件开发者**：希望快速为已有代码生成可运行、有意义的测试套件；
- **代码维护者**：接手遗留代码，需要先建立测试安全网再进行重构；
- **开源项目维护者**：需要快速评估社区提交的代码是否有足够的测试覆盖；
- **AI4SE 学习者/研究者**：希望观察和分析"生成→执行→反馈→修正"闭环的行为特征。

### 1.3 为什么值得做

本项目的核心命题是：**测试生成不是一个"生成"动作，而是一个"生成→验证→修正"的闭环过程**。将这个过程实现为一个 harness，意味着：

1. **客观反馈信号是现成的**：测试要么通过要么失败，编译错误、断言失败、运行时异常都是确定性的信号，无需人工判断；
2. **修正方向是明确的**：失败信息直接指向问题所在（是语法错误、是断言值不对、还是被测代码的 bug），agent 可以据此调整策略；
3. **这一模式可泛化**：任何"生成产物→执行验证→根据反馈修正"的领域（代码生成、文档生成、SQL 生成等）都遵循同样的闭环结构，本项目是这一模式的典型代表。

---

## 2. 用户故事

### US-1: 用户提供一个 Python 函数，系统生成测试套件
**As** 一个开发者  
**I want** 向系统提供一个 Python 函数文件  
**So that** 系统自动生成针对该函数的测试用例  

**验收标准**：系统接受一个 `.py` 文件路径作为输入，输出一个测试文件，包含至少 3 个测试用例。

### US-2: 系统自动运行生成的测试并报告结果
**As** 一个开发者  
**I want** 系统在生成测试后自动执行它们  
**So that** 我能立即知道测试是否通过，而不需要手动运行  

**验收标准**：系统在生成测试后自动执行，并输出每个测试用例的 pass/fail 状态和失败原因。

### US-3: 测试失败时系统自动修正测试代码
**As** 一个开发者  
**I want** 当生成的测试失败时，系统自动分析失败原因并修正测试代码  
**So that** 我不需要手动调试 AI 生成的测试  

**验收标准**：对于因测试代码错误（如错误的断言值、错误的调用方式）导致的失败，系统在最多 N 轮内（N 可配置，默认 3）修正测试使其通过。

### US-4: 系统能区分"测试写错了"和"代码有 bug"
**As** 一个开发者  
**I want** 系统在多次修正后仍无法通过时，明确告诉我"可能是被测代码的问题"  
**So that** 我不会浪费时间让 AI 反复修正一个本来就该失败的测试  

**验收标准**：当达到最大修正轮数后测试仍失败，系统输出诊断报告，区分"测试代码问题"和"疑似被测代码 bug"，并给出证据。

### US-5: 用户可以安全地配置 LLM API Key
**As** 一个用户  
**I want** 在首次运行时被引导安全地录入我的 LLM API Key  
**So that** 我的密钥不会被硬编码、不会进入 Git 历史、不会在屏幕上回显  

**验收标准**：首次运行触发交互式密钥录入（隐藏输入），密钥存储于系统钥匙串或加密文件，可通过命令查看状态（不回显明文）、更新、清除。

### US-6: 用户可以通过一条命令安装和运行
**As** 一个用户  
**I want** 通过 Docker 或 pip 安装本项目，并用一条命令启动  
**So that** 我能在一台新机器上快速开始使用  

**验收标准**：README 提供明确的安装与运行指令，在一台全新的机器上按照指令操作即可运行。

---

## 3. 功能规约

### 3.1 模块总览
┌─────────────────────────────────────────────────────────┐
│ TestForge Harness │
│ │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────┐ │
│ │ 输入解析 │→│ 上下文 │→│ Agent │→│ 工具 │ │
│ │ │ │ 构建 │ │ 主循环 │ │ 分发 │ │
│ └──────────┘ └──────────┘ └──────────┘ └─────────┘ │
│ ↑ ↓ │
│ ┌──────────┐ ┌─────────┐ │
│ │ 反馈 │←│ 测试 │ │
│ │ 校验器 │ │ 执行器 │ │
│ └──────────┘ └─────────┘ │
│ │
│ ┌──────────┐ ┌──────────┐ ┌──────────────────────┐ │
│ │ 治理护栏 │ │ 记忆 │ │ 凭据管理 │ │
│ │ │ │ 管理 │ │ │ │
│ └──────────┘ └──────────┘ └──────────────────────┘ │
└─────────────────────────────────────────────────────────┘

### 3.2 模块详细规约

#### 3.2.1 输入解析模块（Input Parser）

| 项目 | 说明 |
|------|------|
| **输入** | 一个 Python 文件路径（如 `./examples/calculator.py`），以及可选的函数名过滤（如只测试 `add` 和 `subtract`） |
| **行为** | 解析文件，提取所有（或指定的）函数及其签名、docstring、源码 |
| **输出** | 结构化的函数元信息列表：`[{name, args, return_annotation, docstring, source_code, line_range}]` |
| **边界条件** | 文件不存在 → 报错退出；文件无函数 → 报错；语法错误 → 报错并显示 Python 的语法错误信息 |
| **错误处理** | 所有错误统一格式输出到 stderr，退出码非 0 |

#### 3.2.2 Agent 主循环（Agent Loop）

| 项目 | 说明 |
|------|------|
| **输入** | 初始 prompt（包含目标函数信息）、最大迭代轮数、LLM 接口 |
| **行为** | 循环执行：组织上下文 → 调用 LLM → 解析响应中的动作 → 分发给工具执行 → 收集结果 → 判断是否停机 |
| **输出** | 最终状态：成功（测试全部通过）、失败（达到最大轮数）、中止（用户打断或护栏拦截） |
| **边界条件** | LLM 响应无法解析为有效动作 → 将此错误作为反馈回灌给 LLM，消耗一轮迭代；连续 3 次无法解析 → 中止 |
| **停机条件** | ① 测试全部通过；② 达到 `max_iterations`（默认 5）；③ 用户手动打断 |
| **错误处理** | LLM API 调用失败 → 重试 2 次（指数退避）→ 仍失败则中止并报错 |

#### 3.2.3 工具分发（Tool Dispatcher）

Agent 可以执行以下动作（tools）：

| 工具名 | 动作 | 参数 | 返回值 | 是否危险 |
|--------|------|------|--------|----------|
| `write_file` | 写入测试文件 | `path`, `content` | 成功/失败 | 否（限工作目录内） |
| `read_file` | 读取文件 | `path` | 文件内容 | 否 |
| `run_tests` | 运行测试 | `test_path` | 测试结果 JSON | 否 |
| `run_command` | 执行任意 shell 命令 | `command` | stdout/stderr/exit_code | **是，需审批** |

#### 3.2.4 测试执行器（Test Runner）

| 项目 | 说明 |
|------|------|
| **输入** | 测试文件路径、被测试文件路径 |
| **行为** | 在隔离的临时目录中运行 `pytest`，捕获 stdout/stderr |
| **输出** | 结构化 JSON：`{test_cases: [{name, status, error_message, duration}], summary: {total, passed, failed, errors}}` |
| **边界条件** | 测试文件不存在 → 返回错误；pytest 未安装 → 返回明确的环境错误 |
| **安全** | 测试在子进程中运行，设置超时（默认 30 秒），超时强制终止 |

#### 3.2.5 反馈校验器（Feedback Validator）

| 项目 | 说明 |
|------|------|
| **输入** | 测试执行器的结构化输出 |
| **行为** | 分析失败类型，分类为：① `SYNTAX_ERROR`（测试代码语法错误）② `IMPORT_ERROR`（导入错误）③ `ASSERTION_FAILURE`（断言失败）④ `RUNTIME_ERROR`（运行时异常）⑤ `TIMEOUT`（超时）⑥ `ALL_PASSED`（全部通过） |
| **输出** | 失败分类 + 格式化后的反馈消息（包含具体错误信息、失败测试名、相关代码行） |
| **确定性** | 该模块是纯函数，不依赖任何 LLM，输入相同输出必相同 |

#### 3.2.6 治理护栏（Guardrail）

| 项目 | 说明 |
|------|------|
| **拦截规则** | ① `run_command` 必须经过审批；② `write_file` 限制在工作目录内（路径穿越检测）；③ 禁止访问 `.env`、钥匙串、`~/.ssh` 等敏感路径；④ 测试执行器禁止访问网络（通过子进程环境变量隔离） |
| **拦截行为** | 返回 `BLOCKED` 状态 + 原因；如配置为交互模式，则暂停等待用户审批 |
| **确定性** | 护栏是纯函数：`guardrail(action) -> {allowed: bool, reason: str}`，不依赖 LLM |

#### 3.2.7 记忆管理（Memory Manager）

| 项目 | 说明 |
|------|------|
| **存储内容** | 每轮迭代的：LLM 响应、执行的动作、测试结果、失败分类 |
| **检索方式** | 按需提供：最近 3 轮完整记录 + 更早轮次的摘要（通过截断保持 token 预算） |
| **跨会话** | 支持将一次运行的日志保存到 `~/.testforge/history/`，下次运行可选择性加载 |
| **实现** | 自定义实现（文件系统 + JSON），**不依赖任何框架的 memory 机制** |

#### 3.2.8 凭据管理（Credential Manager）

| 项目 | 说明 |
|------|------|
| **威胁模型** | ① 密钥硬编码在源码中被提交到 Git → 泄露；② 密钥通过命令行参数传递 → 进入 shell history；③ 密钥明文存储 → 磁盘泄露；④ 密钥在日志中打印 → 日志泄露 |
| **存储方案** | 首选：操作系统钥匙串（macOS Keychain / Windows Credential Manager / Linux Secret Service via `keyring` 库）；备选：主密码加密文件（AES-256-GCM） |
| **录入流程** | 首次运行时交互式引导：提示用户输入 key（`getpass` 隐藏输入），二次确认，写入钥匙串/加密文件 |
| **查看/更新/清除** | `testforge credential status`（仅显示是否存在和前缀，不回显明文）、`testforge credential set`（覆盖）、`testforge credential clear`（删除） |
| **环境变量** | 支持 `TESTFORGE_API_KEY` 环境变量作为最高优先级来源，但文档中明确标注其明文风险 |

---

## 4. 非功能性需求

### 4.1 性能

- 单轮迭代（LLM 调用 + 测试执行）在正常网络条件下应 < 60 秒；
- 测试执行器超时时间：30 秒（可配置）；
- 整个 harness 启动时间（不含 LLM 调用）< 2 秒。

### 4.2 安全

- 凭据威胁模型与对策：见 §3.2.8；
- 测试在隔离环境中运行（独立子进程 + 环境变量白名单 + 文件系统访问限制）；
- 所有 shell 命令执行前必须经过护栏检查；
- 日志中过滤任何疑似 API key 的模式（如 `sk-[a-zA-Z0-9]{20,}`）。

### 4.3 可用性

- CLI 界面提供清晰的进度显示（当前轮次、动作、测试结果摘要）；
- 错误信息面向用户可操作（如"pytest 未安装，请运行 `pip install pytest`"）；
- 支持 `--verbose` 模式查看完整日志。

### 4.4 可观测性

- 每轮迭代生成结构化日志（JSON 格式）；
- 最终生成一份运行报告（包含：初始输入、每轮动作摘要、最终测试结果、失败分类历史）；
- 支持日志级别：`DEBUG`, `INFO`, `WARN`, `ERROR`。

---

## 5. 系统架构

### 5.1 技术选型与理由

| 组件 | 选择 | 理由 |
|------|------|------|
| 语言 | Python 3.11+ | 目标被测代码为 Python，工具链（pytest、ast）成熟；开发效率高 |
| 测试框架 | pytest | Python 事实标准，结构化输出易于解析 |
| 代码解析 | `ast` 模块（标准库） | 无需外部依赖，可提取函数签名/docstring |
| 凭据存储 | `keyring` 库 | 跨平台钥匙串访问，抽象良好 |
| CLI 框架 | `click` | 成熟稳定，支持子命令 |
| 分发 | Docker + PyPI 包 | Docker 保证环境一致性；PyPI 便于开发者快速安装 |
| CI | GitHub Actions | 仓库托管于 GitHub，原生集成 |

### 5.2 组件图
┌────────────────────────────────────────────────────────────┐
│ CLI (click) │
│ testforge generate ./path/to/file.py --function add │
└──────────────────────┬─────────────────────────────────────┘
│
┌──────────────────────▼─────────────────────────────────────┐
│ Harness Core（自研） │
│ │
│ ┌───────────┐ ┌──────────────┐ ┌──────────────────┐ │
│ │ Input │──▶│ Agent Loop │──▶│ Tool Dispatcher │ │
│ │ Parser │ │ (主循环) │ │ │ │
│ └───────────┘ └──────────────┘ └──────────────────┘ │
│ │ │ │
│ │ ▼ │
│ ┌─────┴─────┐ ┌──────────────┐ │
│ │ Memory │ │ Guardrail │ │
│ │ Manager │ │ (治理护栏) │ │
│ └───────────┘ └──────────────┘ │
│ │ │ │
│ ▼ ▼ │
│ ┌────────────┐ ┌──────────────┐ │
│ │ LLM Client │ │ Test Runner │ │
│ │ (可注入mock)│ │ (隔离执行) │ │
│ └────────────┘ └──────┬───────┘ │
│ │ │
│ ┌─────────▼─────────┐ │
│ │ Feedback │ │
│ │ Validator (核心) │ │
│ └───────────────────┘ │
└────────────────────────────────────────────────────────────┘
│
┌──────────────────────▼─────────────────────────────────────┐
│ Credential Manager (keyring) │
└────────────────────────────────────────────────────────────┘

### 5.3 数据流
用户输入文件路径
→ Input Parser 提取函数信息
→ Agent Loop 构建初始 prompt
→ LLM 响应（生成测试代码 + 动作指令）
→ Tool Dispatcher 识别动作 → Guardrail 检查
→ 通过 → 执行动作（write_file / run_tests）
→ 结果进入 Feedback Validator → 失败分类
→ 反馈回灌 Agent Loop → 下一轮迭代
→ 直到：全部通过 / 达到最大轮数 / 用户中止

---

## 6. 数据模型

### 6.1 核心实体
FunctionInfo {
name: str
args: List[ArgInfo]
return_annotation: str | None
docstring: str | None
source_code: str
file_path: str
line_start: int
line_end: int
}
Action {
tool: str # "write_file" | "read_file" | "run_tests" | "run_command"
params: Dict[str, Any]
request_id: str # 关联到产生此动作的 LLM 响应
}
GuardrailResult {
allowed: bool
reason: str | None
requires_approval: bool
}
TestResult {
test_cases: List[TestCaseResult]
summary: TestSummary
raw_output: str
}
TestCaseResult {
name: str
status: "passed" | "failed" | "error"
error_message: str | None
duration_ms: int
}
FailureClassification {
category: "SYNTAX_ERROR" | "IMPORT_ERROR" | "ASSERTION_FAILURE"
| "RUNTIME_ERROR" | "TIMEOUT" | "ALL_PASSED"
details: str
failed_tests: List[str]
}
IterationRecord {
round: int
llm_response: str
actions: List[Action]
test_result: TestResult | None
failure_classification: FailureClassification | None
timestamp: str
}

### 6.2 关系与约束

- 一个 `FunctionInfo` 对应多次 `IterationRecord`（1:N）；
- 每次迭代产生 0 到多个 `Action`；
- 每个 `Action` 必须经过 `GuardrailResult` 检查后才能执行；
- 每个 `TestResult` 必须经过 `FailureClassification` 分类后才会回灌给 LLM。

---

## 7. 领域与机制设计（Harness 专属）


### 7.1 四类机制设计

#### 7.1.1 动作 / 工具

本项目的 agent 需要以下能力：

| 工具 | 用途 | 对应 coding 场景 |
|------|------|-----------------|
| `write_file` | 写入生成的测试代码 | 编写文件 |
| `read_file` | 读取被测代码或已有测试 | 阅读代码 |
| `run_tests` | 执行测试套件 | 运行测试 |
| `run_command` | 安装依赖等辅助操作 | 执行 shell |

#### 7.1.2 客观反馈信号

**核心信号：测试执行结果。** 这是全过程中最客观、最确定性的反馈：

- 测试通过 = 测试代码可运行且断言与被测代码行为一致；
- 测试失败 = 需要修正，失败类型由 Feedback Validator 确定性分类。

**额外信号**：
- `SYNTAX_ERROR`：测试代码本身无法被 Python 解析；
- `IMPORT_ERROR`：测试代码引用了不存在的模块；
- `TIMEOUT`：测试陷入死循环或无限等待。

这些信号全部由代码产生，不依赖 LLM 判断。

#### 7.1.3 危险动作

| 危险动作 | 风险 | 对策 |
|----------|------|------|
| 任意 shell 命令执行 | 可能删除文件、访问敏感信息 | 必须经过审批；默认在 CLI 中交互式询问 |
| 写入工作目录之外的文件 | 覆盖系统文件 | 路径穿越检测，限制在工作目录内 |
| 测试代码访问网络 | 数据外泄 | 测试子进程禁止网络访问 |
| 读取敏感文件（`.env`、`.ssh`、钥匙串） | 凭据泄露 | 路径黑名单，护栏直接拦截 |

#### 7.1.4 记忆

- **短期记忆**（同一 session 内）：最近 3 轮完整迭代记录自动包含在上下文中；更早轮次以摘要形式提供；
- **长期记忆**（跨 session）：运行历史保存在 `~/.testforge/history/`，用户可选择性加载之前的运行记录；
- **记忆约束**：每次 LLM 调用的上下文不超过预设 token 预算（默认 8000 tokens），超出时按"最近优先"原则截断。

### 7.2 重点维度：反馈闭环（Feedback Loop）

**为什么选择反馈闭环作为重点维度？**

1. 这是本项目"测试生成器"区别于现有工具的核心差异——不是生成完就结束，而是形成一个真正的闭环；
2. 反馈信号（测试结果）是确定性的，最适合用代码实现；
3. 失败分类是一个有信息量的工程问题：不同类型的失败需要不同格式的反馈消息，这直接影响 LLM 的修正效率。

### 7.3 机制编码实现（回应 §A.4）



| 机制 | 编码实现方式 | 确定性测试方式 |
|------|-------------|---------------|
| 主循环 | `AgentLoop.run()` 方法：构建上下文→调用 LLM→解析动作→分发→收集反馈→判断停机 | Mock LLM 返回预设响应序列，验证循环按预期停止 |
| 工具分发 | `ToolDispatcher.dispatch(action)` 方法：根据 `action.tool` 路由到对应 handler | 传入构造的 Action，验证调用了正确的 handler |
| 护栏 | `Guardrail.check(action) -> GuardrailResult`：纯函数 | 直接传入危险 Action，断言被拦截 |
| 反馈校验 | `FeedbackValidator.classify(test_result) -> FailureClassification`：纯函数 | 传入构造的 TestResult，断言分类正确 |
| 测试执行 | `TestRunner.run(test_path)`：子进程运行 pytest，解析输出 | 用 fixture 创建真实的测试文件，验证输出解析 |
| 记忆 | `MemoryManager.append(record)` / `get_recent(n)`：文件系统 + JSON | 直接测试读写逻辑 |
| 停机判断 | `AgentLoop._should_stop(state) -> bool`：纯函数 | 传入各种状态，验证停机条件 |

**明确不属于实现工作量的内容**：所有 prompt 模板、系统提示词、LLM 输出格式说明——这些是"内容物"，不计数。

---

## 8. 凭据与分发设计

### 8.1 凭据存储方案

**首选方案：操作系统钥匙串**

- 使用 Python `keyring` 库访问系统钥匙串；
- 存储位置：macOS Keychain / Windows Credential Manager / Linux Secret Service；
- 无钥匙串环境（如无头 Linux 服务器）回退到加密文件方案。

**回退方案：主密码加密文件**

- 文件位置：`~/.testforge/credentials.enc`；
- 加密算法：AES-256-GCM，密钥由用户主密码通过 PBKDF2 派生；
- 首次使用时引导用户设置主密码。

### 8.2 录入 / 查看 / 更新 / 清除流程

```bash
# 首次运行（自动触发）
$ testforge generate ./example.py
[TestForge] 未检测到 API Key，是否现在配置？[Y/n] Y
[TestForge] 请输入 API Key（输入不会显示）：
[TestForge] 请再次确认 API Key：
[TestForge] API Key 已安全存储到系统钥匙串。

# 查看状态
$ testforge credential status
状态：已配置
来源：macOS Keychain
前缀：sk-...a3f2
（不回显完整明文）

# 更新
$ testforge credential set
请输入新的 API Key（输入不会显示）：

# 清除
$ testforge credential clear
已清除存储的 API Key。
8.3 分发形态
主要分发方式：PyPI 包
pip install testforge
testforge generate ./path/to/your/code.py

8.4 目标平台
• 开发平台：macOS（Apple Silicon / Intel）、Linux（x86_64）、Windows（可选，通过 WSL 保证兼容）
• 运行时要求：Python 3.11+，pytest 7.0+
• 已知限制：Windows 原生支持不是优先事项，推荐 WSL2
9. 验收标准

编号     功能         客观判定标准
AC-1    输入解析      传入一个含 3 个函数的 Python 文件，解析出 3 个 FunctionInfo，字段完整
AC-2    测试生成      对 add(a, b) 函数，生成的测试文件包含至少 3 个测试用例且覆盖正常/边界/异常场景
AC-3    自动运行      生成后自动执行测试，输出包含每个用例的 pass/fail 状态
AC-4    自动修正      故意让 LLM 第一轮生成错误断言，系统在 3 轮内修正并通过
AC-5    bug 诊断      对本身有 bug 的函数（如 add 实现为 a - b），系统在达到最大轮数后明确报告"疑似被测代码问题"
AC-6    凭据安全       代码库中搜索不到任何 API key；credential status 不回显明文；key 不在 shell history 中
AC-7    护栏拦截       传入 run_command("rm -rf /") 动作，护栏返回 BLOCKED（有确定性单测覆盖）
AC-8    Mock LLM 测试 全部核心机制在 mock LLM 下有确定性单测，离线可运行（pytest --offline）
AC-9    分发          在全新环境按 README 指令可安装并成功运行（用 mock LLM 验证）
AC-10   CI            GitHub Actions 配置了 unit-test job，最后一次 commit 的 CI 状态为 pass

10. 风险与未决问题
10.1 已识别的风险

风险                          影响                      缓解措施
LLM 生成的测试代码格式不可预测  测试文件无法被 pytest 解析 在 prompt 中明确输出格式；Feedback Validator 将语法错误作为最高优先级反馈
LLM "偷看"实现细节后生成"过拟合"测试 测试质量低，只是机械重复实现逻辑 在 prompt 中只提供函数签名和 docstring，不提供完整源码（作为可配置选项）
LLM 修正方向错误，反复修改无关部分 浪费迭代轮数 失败分类精确指向问题；上下文包含上一轮的失败信息
测试执行器被恶意测试代码利用 安全风险 子进程隔离 + 超时 + 网络禁用 + 文件系统只读
不同 LLM 供应商的输出格式差异 解析失败 LLM 抽象层标准化输入输出；支持多种 provider 的 adapter
.env 文件被误提交 凭据泄露 .gitignore 中明确列出；CI 中扫描；README 中警告
10.2 未决问题
1. 是否向 LLM 提供被测函数的完整源码？ 如果提供，测试质量可能更高（能覆盖更多分支），但有"过拟合"风险。初版方案：默认只提供签名和 docstring，用户可通过 --include-source 开启完整源码。
2. 测试覆盖率如何度量？ 是否在闭环中加入 coverage 作为额外反馈信号？初版方案：不加入，保持反馈信号简单（pass/fail），coverage 作为未来扩展。
3. 多函数同时测试的上下文管理？ 如果用户提供包含 10 个函数的文件，如何分批处理？初版方案：逐函数处理，用户可通过 --function 指定。

附录 A：Mock LLM 设计
Mock LLM 是验证 harness 机制的关键组件。它不调用任何外部 API，而是：
• 从预设的"脚本"中读取响应序列；
• 每条响应包含：要输出的内容（模拟 LLM 生成测试代码）+ 要执行的动作；
• 支持错误注入：在指定轮次返回格式错误的响应，验证 harness 的容错能力。
# 示例：mock_llm.py
class MockLLM:
    def __init__(self, script: List[LLMResponse]):
        self.script = script
        self.call_count = 0
    
    def complete(self, messages: List[Dict]) -> str:
        if self.call_count >= len(self.script):
            raise StopIteration("Mock LLM 脚本耗尽")
        response = self.script[self.call_count]
        self.call_count += 1
        return response.content

附录 B：项目目录结构（预期）
testforge/
├── testforge/
│   ├── __init__.py
│   ├── cli.py              # CLI 入口
│   ├── core/
│   │   ├── agent_loop.py   # 主循环（自研）
│   │   ├── tool_dispatcher.py # 工具分发（自研）
│   │   ├── guardrail.py    # 治理护栏（自研）
│   │   └── feedback.py     # 反馈校验器（自研，重点）
│   ├── tools/
│   │   ├── file_tools.py   # 文件读写工具
│   │   └── test_runner.py  # 测试执行器
│   ├── llm/
│   │   ├── base.py         # LLM 抽象层
│   │   ├── openai_client.py # OpenAI 实现
│   │   └── mock_client.py  # Mock 实现
│   ├── memory/
│   │   └── manager.py      # 记忆管理（自研）
│   ├── credentials/
│   │   └── manager.py      # 凭据管理
│   └── parser/
│       └── function_parser.py # 输入解析
├── tests/
│   ├── unit/               # 确定性单元测试（mock LLM）
│   ├── fixtures/           # 测试用 fixture
│   └── integration/        # 集成测试
├── examples/               # 示例项目
├── Dockerfile
├── pyproject.toml
├── .github/workflows/ci.yml
├── .gitlab-ci.yml
├── README.md
├── SPEC.md
├── PLAN.md
├── SPEC_PROCESS.md
├── AGENT_LOG.md
└── REFLECTION.md