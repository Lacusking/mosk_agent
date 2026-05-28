# 自研 Agent Platform 产品需求文档（PRD）

版本：v0.1  
状态：Draft  
目标实现语言：Python  
产品定位：Pattern-driven、Runtime-driven、Multi-Agent、Tool-Governed、Memory-Aware 的自研 Agent Platform

---

## 1. 文档目的

本文档用于定义自研 Agent Platform 的产品目标、核心能力、用户场景、模块边界、功能需求、非功能需求、技术架构、迭代路线和验收标准。

本 PRD 面向以下角色：

- 产品负责人：明确平台边界、版本范围、交付优先级。
- 架构师：明确系统分层、模块职责、核心链路。
- 后端工程师：明确 Python 项目结构、服务职责、接口边界。
- AI 工程师：明确 Agent Runtime、Prompt、Skill、Memory、Tool、Multi-Agent 的实现要求。
- 安全与平台工程师：明确权限、审计、沙箱、治理和可观测要求。
- 测试与评估工程师：明确评估体系、回放机制、验收指标。

---

## 2. 产品背景

随着 LLM 从对话助手演进为具备规划、工具调用、环境交互、记忆管理和多智能体协作能力的 Agent 系统，单纯调用模型 API 已无法满足复杂业务自动化需求。

当前市场上已有 ADK、LangGraph、Deep Agents、Claude Code、Codex、Strands Agents、OpenClaw、Pi 等方案，但它们分别存在以下限制：

- 部分框架偏模型或云厂商绑定。
- 部分产品偏封闭式 coding agent，难以作为自有平台底座。
- 部分开源框架只提供 agent loop 或 tool abstraction，缺少完整的 memory、VFS、policy、sandbox、evaluation、deployment 能力。
- 多智能体、技能包、生命周期 hook、prompt 模板治理等能力往往分散实现，缺少统一平台架构。

因此需要构建一个完全自研、模型无关、工具可治理、记忆可审计、多智能体原生、可回放可评估的 Agent Platform。

---

## 3. 产品定位

### 3.1 一句话定位

构建一个 Python 实现的企业级 Agent Platform，用于支持多模型接入、Prompt 模板管理、Skill 能力复用、Hook 生命周期扩展、Tool 安全执行、多智能体协作、长期记忆管理、VFS 文件边界、沙箱执行、治理审计、评估回放和平台化部署。

### 3.2 产品形态

平台最终包含以下形态：

1. Python SDK：供开发者构建 Agent、Skill、Tool、Workflow。
2. Runtime Service：负责执行任务、调度 Agent、处理事件流。
3. API Server：对外提供任务、会话、工具、记忆、产物、评估等接口。
4. CLI：本地调试、运行、回放、评估。
5. Worker Pool：异步执行模型调用、工具调用、沙箱任务、记忆整理、评估任务。
6. Control Plane：管理 Agent、Skill、Tool、Prompt、Policy、Deployment。
7. Observability & Evaluation Console：跟踪执行轨迹、成本、质量、错误和回归。

### 3.3 产品边界

本平台不是：

- 单纯 Chatbot。
- 单纯 Prompt 管理工具。
- 单纯 RAG 系统。
- 单纯 Workflow 引擎。
- 单纯 Coding Agent。
- 单纯 MCP Client。

本平台是这些能力之上的统一 Agent Runtime 与治理平台。

---

## 4. 产品目标

### 4.1 业务目标

| 目标 | 描述 |
|---|---|
| 可复用 | 通过 Skill Engine 将 Prompt、Tool、Workflow、Policy、Memory Scope 组合为可复用能力包。 |
| 可治理 | 所有模型调用、工具调用、记忆写入、文件访问、沙箱执行都经过权限、策略、审计和 Hook。 |
| 可扩展 | 支持插件式 Tool、Skill、Hook、Model Adapter、Connector 扩展。 |
| 可观测 | 所有 Agent 执行步骤具备 trace、event、cost、latency、token、tool span。 |
| 可评估 | 支持 trajectory eval、tool eval、answer eval、prompt eval、regression eval。 |
| 可回放 | 通过 event sourcing 支持任务回放、debug、复现和失败分析。 |
| 多智能体原生 | 支持 Supervisor、Subagent、Role Agent、A2A、结果聚合和上下文隔离。 |
| 模型无关 | 支持 OpenAI、Anthropic、Gemini、Ollama、LiteLLM 等模型适配。 |

### 4.2 技术目标

- Python monorepo + src layout。
- 模块化、强 schema、事件驱动、可测试。
- 核心协议统一放入 contracts/。
- 运行时采用 Event Sourcing。
- 所有可变资产支持版本：Prompt、Skill、Tool、Policy、Workflow、Agent。
- 所有高风险动作必须可审计、可审批、可回滚或可隔离。

---

## 5. 目标用户与使用场景

### 5.1 目标用户

| 用户类型 | 核心需求 |
|---|---|
| AI 应用开发者 | 快速构建自定义 Agent、Tool、Skill、Workflow。 |
| 平台工程师 | 维护统一运行时、权限、沙箱、监控、部署体系。 |
| 企业业务团队 | 通过 Skill 或 Agent 自动化研究、报告、数据分析、代码审查等任务。 |
| 安全与合规人员 | 审查工具权限、数据访问、审计日志、记忆写入。 |
| 评估工程师 | 构建 eval 数据集，做回归测试与质量评估。 |
| 管理员 | 管理租户、用户、Agent、Skill、Tool、Policy 和版本发布。 |

### 5.2 典型场景

#### 场景一：研究报告 Agent

用户输入研究主题，Agent 自动完成：

1. 任务路由。
2. 计划生成。
3. 并行检索。
4. 资料摘要。
5. 多智能体协作分析。
6. 事实核查。
7. 报告生成。
8. 引用整理。
9. Artifact 保存。
10. 评估与回放。

#### 场景二：代码审查 Agent

用户提交 Git diff，Agent 自动完成：

1. 加载 coding_review skill。
2. 读取代码变更。
3. 运行静态检查或测试。
4. 生成问题列表。
5. Critic Agent 复审。
6. 输出结构化 Review Report。
7. 可选创建 GitHub Review Comment。

#### 场景三：数据分析 Agent

用户上传 CSV 或数据库查询任务，Agent 自动完成：

1. 读取数据文件。
2. 生成分析计划。
3. 在沙箱中运行 Python 分析。
4. 生成图表和结论。
5. 输出 notebook、报告和数据产物。

#### 场景四：多智能体业务流程自动化

Supervisor Agent 将任务分解给多个角色 Agent：

- Research Agent
- Executor Agent
- Critic Agent
- Writer Agent

最终进行结果聚合、审查和交付。

---

## 6. 整体架构

### 6.1 模块目录

```text
src/agent_platform/
├── access/
├── identity/
├── api/
├── cli/
├── core/
├── contracts/
├── runtime/
├── events/
├── agent_runs/
├── tasks/
├── sessions/
├── scheduler/
├── models/
├── prompts/
├── skills/
├── hooks/
├── patterns/
├── workflow/
├── agents/
├── multi_agent/
├── tools/
├── connectors/
├── context/
├── memory/
├── knowledge/
├── rag/
├── vfs/
├── artifacts/
├── sandbox/
├── policy/
├── governance/
├── observability/
├── evaluation/
├── experiments/
├── notifications/
├── control_plane/
├── deployment/
├── storage/
├── workers/
└── plugins/
```

### 6.2 分层架构

| 层级 | 目录 | 职责 |
|---|---|---|
| 接入与身份层 | access, identity, api, cli | 请求接入、认证授权、租户绑定、API/CLI 入口。 |
| 控制面与部署层 | control_plane, deployment, plugins | Agent/Skill/Tool/Prompt/Policy 管理，版本发布，插件扩展。 |
| 运行时核心层 | runtime, events, agent_runs, sessions, scheduler, workers | Agent 事件循环、AgentRun 生命周期、事件流、会话、调度、异步执行。 |
| 智能编排层 | models, prompts, skills, hooks, patterns, workflow | 模型适配、Prompt 编译、Skill 能力包、Hook 扩展、设计模式、工作流。 |
| Agent 层 | agents, multi_agent | Agent 抽象、多智能体编排、Subagent、A2A、结果聚合。 |
| 工具与集成层 | tools, connectors, sandbox | 工具注册、工具执行、外部系统连接、隔离执行。 |
| 上下文、记忆与知识层 | context, memory, knowledge, rag | 上下文组装、长期记忆、知识库、检索增强。 |
| 数据与产物层 | vfs, artifacts, storage | 虚拟文件系统、产物管理、数据库、对象存储、向量库。 |
| 治理与安全层 | policy, governance | 策略判断、权限、审批、护栏、审计、密钥、合规。 |
| 可观测、评估与实验层 | observability, evaluation, experiments, notifications | trace、metrics、cost、评估、回归、实验、通知。 |
| 公共基础层 | core, contracts | 公共工具、错误、Schema、协议、数据契约。 |

### 6.3 主执行链路

```text
Request
→ Access Normalize
→ Identity Resolve
→ Runtime Create AgentRun
→ Hook before_agent_run_start
→ Skill Resolve
→ Prompt Pack Load
→ Context Assemble
→ Pattern Orchestration
→ Model Call
→ Tool Request
→ Tool Governance
→ Sandbox / Connector / VFS Execute
→ Tool Observation
→ Reflection / Evaluation
→ Memory Write Policy
→ Artifact Persist
→ Event Log
→ Final Response
```

---

## 7. 核心功能需求

## 7.1 Access Layer

### 需求说明

Access Layer 负责接收来自 Web、API、CLI、Webhook、A2A Agent、MCP Client 的请求，并统一转换为平台内部 AgentRequest。

### 功能点

| 编号 | 功能 | 优先级 |
|---|---|---|
| ACC-001 | 支持 HTTP API 请求接入 | P0 |
| ACC-002 | 支持 CLI 本地运行任务 | P0 |
| ACC-003 | 支持 Webhook 任务触发 | P1 |
| ACC-004 | 支持 A2A Agent 调用入口 | P1 |
| ACC-005 | 支持 MCP Client 接入 | P1 |
| ACC-006 | 请求标准化为 AgentRequest | P0 |
| ACC-007 | 注入 AccessContext，包括 user、tenant、project、roles、scopes | P0 |

### AgentRequest Schema

```python
class AgentRequest(BaseModel):
    request_id: str
    tenant_id: str
    user_id: str
    project_id: str | None = None
    channel: Literal["web", "api", "cli", "webhook", "a2a", "mcp"]
    session_id: str | None = None
    goal: str
    input: dict[str, Any]
    constraints: dict[str, Any] = {}
    metadata: dict[str, Any] = {}
```

---

## 7.2 Identity Layer

### 需求说明

Identity Layer 负责用户、租户、项目、角色、权限、API Key、Service Account 的管理。

### 功能点

| 编号 | 功能 | 优先级 |
|---|---|---|
| ID-001 | 用户与租户模型 | P0 |
| ID-002 | API Key 鉴权 | P0 |
| ID-003 | RBAC 权限模型 | P0 |
| ID-004 | Project Scope | P1 |
| ID-005 | Service Account | P1 |
| ID-006 | ABAC 条件权限 | P2 |
| ID-007 | 多租户隔离 | P0 |

---

## 7.3 Runtime Core

### 需求说明

Runtime 是整个平台的执行内核，负责驱动 AgentRun 生命周期、事件循环、状态机、模型调用、工具调用、Hook 分发、checkpoint、replay。Task 另指未来由 planning 驱动的计划/待办引擎，不是 runtime 执行单元。

### 功能点

| 编号 | 功能 | 优先级 |
|---|---|---|
| RT-001 | 创建 AgentRun | P0 |
| RT-002 | Event Loop 执行 Agent Step | P0 |
| RT-003 | 状态机管理 AgentRun 状态 | P0 |
| RT-004 | Step Runner 执行模型/工具/Agent/Human 步骤 | P0 |
| RT-005 | 支持 max_steps、timeout、cost_budget | P0 |
| RT-006 | 支持 checkpoint | P1 |
| RT-007 | 支持 replay | P1 |
| RT-008 | 支持 cancellation | P1 |
| RT-009 | 支持 heartbeat | P1 |
| RT-010 | 支持并发调度 | P1 |

### AgentRun 状态

```text
CREATED
→ RUNNING
→ COMPLETED

异常分支：
RUNNING → FAILED
RUNNING → CANCELLED

说明：`routing`、`planning`、`react` 和 `reflection` 属于可组合或可切换的 Pattern 执行策略，通过 run step 和事件记录，不进入顶层生命周期状态。等待工具、人审和恢复状态随对应能力引入。
```

---

## 7.4 Events

### 需求说明

Events 模块提供 Event Sourcing 能力，是 trace、audit、replay、eval、debug 的事实来源。

### 功能点

| 编号 | 功能 | 优先级 |
|---|---|---|
| EVT-001 | 统一 RuntimeEvent | P0 |
| EVT-002 | Event Store 持久化 | P0 |
| EVT-003 | Event Bus 分发 | P1 |
| EVT-004 | Event Stream 查询 | P1 |
| EVT-005 | 支持 replay by agent_run_id | P1 |
| EVT-006 | 支持 event schema version | P1 |

### 关键事件类型

```text
AgentRunCreated
AgentRunStarted
RouteDecided
SkillResolved
PromptRendered
ModelCalled
ToolRequested
ToolApproved
ToolExecuted
SubAgentCreated
SubAgentCompleted
MemoryCandidateGenerated
MemoryWritten
ArtifactCreated
ReflectionCompleted
AgentRunCompleted
AgentRunFailed
```

---

## 7.5 Model Adapter

### 需求说明

Models 模块负责统一不同模型供应商接口。

### 功能点

| 编号 | 功能 | 优先级 |
|---|---|---|
| MOD-001 | OpenAI Adapter | P0 |
| MOD-002 | Anthropic Adapter | P1 |
| MOD-003 | Gemini Adapter | P1 |
| MOD-004 | Ollama Adapter | P1 |
| MOD-005 | LiteLLM Adapter | P1 |
| MOD-006 | Model Selector | P0 |
| MOD-007 | Token Usage 统一统计 | P0 |
| MOD-008 | Streaming 支持 | P1 |
| MOD-009 | Tool Calling 统一抽象 | P0 |
| MOD-010 | Structured Output 支持 | P0 |

### ModelAdapter 接口

```python
class ModelAdapter(Protocol):
    name: str
    supports: ModelCapabilities

    async def invoke(self, request: ModelRequest) -> ModelResponse:
        ...

    async def stream(self, request: ModelRequest) -> AsyncIterator[ModelStreamEvent]:
        ...
```

---

## 7.6 Prompt Engine

### 需求说明

Prompt Engine 负责 Prompt 模板、变量解析、上下文注入、模型格式化、版本管理、结构化输出绑定、Prompt 安全和评估。

### 功能点

| 编号 | 功能 | 优先级 |
|---|---|---|
| PRM-001 | Prompt Template Registry | P0 |
| PRM-002 | Prompt Loader | P0 |
| PRM-003 | Prompt Renderer | P0 |
| PRM-004 | Variable Resolver | P0 |
| PRM-005 | OpenAI/Anthropic/Gemini 格式化 | P0 |
| PRM-006 | Output Schema Binder | P0 |
| PRM-007 | Prompt Versioning | P1 |
| PRM-008 | Prompt Cache | P1 |
| PRM-009 | Prompt Injection Guard Hook | P1 |
| PRM-010 | Prompt Evaluation Dataset 绑定 | P2 |

### Prompt 资产结构

```text
prompts/builtin/planner/
├── prompt.yaml
├── system.md
├── create_plan.md
├── revise_plan.md
└── output.schema.json
```

---

## 7.7 Skill Engine

### 需求说明

Skill Engine 负责将 Prompt、Tool、Workflow、Policy、Hook、Memory Scope、Output Schema 组合为可复用能力包。

### 功能点

| 编号 | 功能 | 优先级 |
|---|---|---|
| SKL-001 | Skill Manifest 定义 | P0 |
| SKL-002 | Skill Registry | P0 |
| SKL-003 | 本地 Skill Loader | P0 |
| SKL-004 | Skill Resolver | P0 |
| SKL-005 | Skill Tool Scope 限制 | P0 |
| SKL-006 | Skill Prompt Pack 加载 | P0 |
| SKL-007 | Skill Policy 注入 | P1 |
| SKL-008 | Skill Hook 注入 | P1 |
| SKL-009 | Skill Versioning | P1 |
| SKL-010 | Skill Packaging | P2 |
| SKL-011 | Skill Marketplace Source | P3 |

### Skill 示例

```yaml
name: coding_review
version: 0.1.0
prompts:
  system: prompts/system.md
  entry: prompts/review.md
tools:
  allowed:
    - git.diff
    - vfs.read
    - shell.run_tests
patterns:
  - planning
  - reflection
memory:
  read:
    - project_conventions
  write:
    mode: propose
hooks:
  before_tool_call:
    - tool_risk_guard
```

---

## 7.8 Hook Engine

### 需求说明

Hook Engine 负责在 Runtime、Prompt、Model、Tool、Memory、VFS、Sandbox、Evaluation 等生命周期节点插入拦截逻辑。

### 功能点

| 编号 | 功能 | 优先级 |
|---|---|---|
| HOK-001 | Hook Registry | P0 |
| HOK-002 | Hook Manager | P0 |
| HOK-003 | Hook Priority | P0 |
| HOK-004 | Hook Result: continue / modify / block | P0 |
| HOK-005 | before_model_call | P0 |
| HOK-006 | after_model_call | P0 |
| HOK-007 | before_tool_call | P0 |
| HOK-008 | after_tool_call | P0 |
| HOK-009 | before_memory_write | P0 |
| HOK-010 | on_agent_run_error | P0 |
| HOK-011 | before_prompt_send | P1 |
| HOK-012 | sandbox violation hooks | P1 |

### 内置 Hooks

```text
tracing
audit
cost_tracking
pii_redaction
prompt_injection_guard
tool_risk_guard
memory_write_guard
retry_policy
telemetry
```

---

## 7.9 Pattern Engine

### 需求说明

Patterns 模块提供 Agentic Design Patterns 的工程实现。

### 功能点

| 编号 | 模式 | 功能 | 优先级 |
|---|---|---|---|
| PAT-001 | Single Turn | 单次直接响应基础策略 | P0 |
| PAT-002 | Prompt Chaining | ChainRunner | P0 |
| PAT-003 | Routing | Rule/LLM Router 与策略切换 | P0 |
| PAT-004 | Planning | 规划推理策略，不实现持久化 Task Engine | P0 |
| PAT-005 | ReAct | model/action/observation 循环策略 | P0 |
| PAT-006 | Reflection | Critic/Verifier/Reviser | P0 |
| PAT-007 | Parallelization | Fan-out/Fan-in | P1 |
| PAT-008 | Resource Optimization | Model/Cost/Latency Selector | P2 |
| PAT-009 | Debate | 多候选辩论 | P2 |
| PAT-010 | Self-Correction | 自动修正 | P2 |

---

## 7.10 Workflow Engine

### 需求说明

Workflow 负责确定性任务流程执行，与 Planning 不同，Workflow 是可版本化、可回放、可补偿的执行流程。

### 功能点

| 编号 | 功能 | 优先级 |
|---|---|---|
| WFL-001 | Workflow Definition | P0 |
| WFL-002 | Workflow Runner | P0 |
| WFL-003 | DAG Step | P0 |
| WFL-004 | Conditional Transition | P1 |
| WFL-005 | Retry Policy | P1 |
| WFL-006 | Compensation | P2 |
| WFL-007 | Workflow Versioning | P1 |

---

## 7.11 Agents

### 需求说明

Agents 模块定义可执行主体，包括 Base Agent、Supervisor、Worker、Role Agent、Builtin Agent。

### 功能点

| 编号 | 功能 | 优先级 |
|---|---|---|
| AGT-001 | BaseAgent 抽象 | P0 |
| AGT-002 | AgentCard | P0 |
| AGT-003 | Agent Registry | P0 |
| AGT-004 | SupervisorAgent | P1 |
| AGT-005 | WorkerAgent | P1 |
| AGT-006 | RoleAgent | P1 |
| AGT-007 | Builtin ResearchAgent | P1 |
| AGT-008 | Builtin CodingAgent | P1 |

---

## 7.12 Multi-Agent

### 需求说明

Multi-Agent 模块负责多智能体任务委派、上下文隔离、通信协议、结果聚合。

### 功能点

| 编号 | 功能 | 优先级 |
|---|---|---|
| MAG-001 | MultiAgent Orchestrator | P1 |
| MAG-002 | Ephemeral Subagent | P1 |
| MAG-003 | Delegation | P1 |
| MAG-004 | Context Isolation | P1 |
| MAG-005 | Result Collection | P1 |
| MAG-006 | Hierarchical Pattern | P1 |
| MAG-007 | Role-based Pattern | P1 |
| MAG-008 | Debate Pattern | P2 |
| MAG-009 | A2A Internal Protocol | P2 |
| MAG-010 | MCP Integration Boundary | P2 |

---

## 7.13 Tools

### 需求说明

Tools 模块负责工具注册、路由、执行、权限、重试、幂等、结果格式化。

### 功能点

| 编号 | 功能 | 优先级 |
|---|---|---|
| TOL-001 | ToolDefinition | P0 |
| TOL-002 | ToolRegistry | P0 |
| TOL-003 | ToolRouter | P0 |
| TOL-004 | ToolExecutor | P0 |
| TOL-005 | Tool Schema Validation | P0 |
| TOL-006 | Tool Risk Level | P0 |
| TOL-007 | Tool Permission Scope | P0 |
| TOL-008 | Retry & Idempotency | P1 |
| TOL-009 | Tool Observation Formatter | P0 |
| TOL-010 | Builtin filesystem/http/database/python tools | P1 |
| TOL-011 | MCP Tool Adapter | P1 |

---

## 7.14 Connectors

### 需求说明

Connectors 负责外部系统 API 封装、认证、限流、凭据管理。

### 功能点

| 编号 | Connector | 优先级 |
|---|---|---|
| CON-001 | GitHub Connector | P1 |
| CON-002 | Slack Connector | P1 |
| CON-003 | Jira Connector | P2 |
| CON-004 | Google Drive Connector | P2 |
| CON-005 | PostgreSQL Connector | P1 |
| CON-006 | Browser/Web Connector | P1 |
| CON-007 | Connector Credential Binding | P0 |
| CON-008 | Connector Rate Limit | P1 |

---

## 7.15 Context Manager

### 需求说明

Context 模块负责将 session、agent run、memory、rag、vfs、tool observations 组装为模型可用上下文。

### 功能点

| 编号 | 功能 | 优先级 |
|---|---|---|
| CTX-001 | Context Assembler | P0 |
| CTX-002 | Context Budget | P0 |
| CTX-003 | Context Compressor | P1 |
| CTX-004 | Tool Observation Formatter | P0 |
| CTX-005 | Structured Output Parser | P0 |
| CTX-006 | Model-specific Context Formatting | P0 |

---

## 7.16 Memory

### 需求说明

Memory 模块负责 Session、Working、Summary、Semantic、Entity、Episodic Memory，以及记忆写入、更新、遗忘、冲突解决和检索策略。

### 功能点

| 编号 | 功能 | 优先级 |
|---|---|---|
| MEM-001 | Session Memory | P0 |
| MEM-002 | Working Memory | P0 |
| MEM-003 | Summary Memory | P0 |
| MEM-004 | Semantic Memory | P1 |
| MEM-005 | Entity Memory | P1 |
| MEM-006 | Episodic Memory | P2 |
| MEM-007 | Memory Write Policy | P0 |
| MEM-008 | Memory Conflict Resolution | P1 |
| MEM-009 | Memory Forget Policy | P1 |
| MEM-010 | Memory Search | P1 |
| MEM-011 | Memory Consolidation | P2 |

---

## 7.17 Knowledge & RAG

### 需求说明

Knowledge 负责知识资产管理，RAG 负责运行时检索增强。

### 功能点

| 编号 | 功能 | 优先级 |
|---|---|---|
| KNO-001 | Document Ingestion | P1 |
| KNO-002 | Parser: PDF/Markdown/HTML/Code | P1 |
| KNO-003 | Chunking | P1 |
| KNO-004 | Metadata & Provenance | P1 |
| KNO-005 | Corpus Permission | P1 |
| RAG-001 | Retriever | P1 |
| RAG-002 | Embeddings | P1 |
| RAG-003 | Reranker | P2 |
| RAG-004 | Citation | P1 |
| RAG-005 | Grounding Formatter | P1 |

---

## 7.18 VFS

### 需求说明

VFS 提供 `/workspace`、`/artifacts`、`/memories` 的虚拟文件边界，统一文件访问、快照、diff、权限和后端存储。

### 功能点

| 编号 | 功能 | 优先级 |
|---|---|---|
| VFS-001 | Path Abstraction | P0 |
| VFS-002 | Workspace Mount | P0 |
| VFS-003 | Artifacts Mount | P0 |
| VFS-004 | Memories Mount | P1 |
| VFS-005 | Local Backend | P0 |
| VFS-006 | Object Storage Backend | P1 |
| VFS-007 | Snapshot | P1 |
| VFS-008 | Diff | P1 |
| VFS-009 | VFS Permission | P0 |

---

## 7.19 Artifacts

### 需求说明

Artifacts 模块负责生成物生命周期，包括报告、代码补丁、数据集、图表、notebook、文件、截图等。

### 功能点

| 编号 | 功能 | 优先级 |
|---|---|---|
| ART-001 | Artifact Metadata | P0 |
| ART-002 | Artifact Versioning | P1 |
| ART-003 | Artifact Preview | P1 |
| ART-004 | Artifact Export | P1 |
| ART-005 | Artifact Lineage | P1 |
| ART-006 | Retention Policy | P2 |

---

## 7.20 Sandbox

### 需求说明

Sandbox 负责隔离执行高风险工具，包括 Python、Shell、Browser、Docker、Firecracker、Remote Runner。

### 功能点

| 编号 | 功能 | 优先级 |
|---|---|---|
| SBX-001 | Sandbox Policy | P0 |
| SBX-002 | Python Runner | P1 |
| SBX-003 | Docker Runner | P1 |
| SBX-004 | Subprocess Runner for dev only | P0 |
| SBX-005 | Network Policy | P1 |
| SBX-006 | Filesystem Policy | P1 |
| SBX-007 | Resource Limits | P1 |
| SBX-008 | Browser Runner | P2 |
| SBX-009 | Firecracker Runner | P3 |

---

## 7.21 Policy & Governance

### 需求说明

Policy 负责策略判断，Governance 负责风险治理、审批、审计、密钥、合规和护栏。

### 功能点

| 编号 | 功能 | 优先级 |
|---|---|---|
| POL-001 | Policy Engine | P0 |
| POL-002 | Tool Policy | P0 |
| POL-003 | Memory Policy | P0 |
| POL-004 | Sandbox Policy | P1 |
| POL-005 | Model Policy | P1 |
| GOV-001 | Risk Classifier | P0 |
| GOV-002 | Human Approval | P1 |
| GOV-003 | Audit Log | P0 |
| GOV-004 | Secret Scope | P1 |
| GOV-005 | Guardrails | P1 |
| GOV-006 | Compliance Rules | P2 |

---

## 7.22 Observability

### 需求说明

Observability 负责 trace、metrics、logging、cost、token usage、alerts。

### 功能点

| 编号 | 功能 | 优先级 |
|---|---|---|
| OBS-001 | Trace ID / Span ID | P0 |
| OBS-002 | Runtime Span | P0 |
| OBS-003 | Model Call Metrics | P0 |
| OBS-004 | Tool Call Metrics | P0 |
| OBS-005 | Cost Tracking | P0 |
| OBS-006 | Token Usage | P0 |
| OBS-007 | Alerts | P1 |
| OBS-008 | Dashboard Export | P2 |

---

## 7.23 Evaluation

### 需求说明

Evaluation 负责轨迹评估、工具评估、答案评估、安全评估、成本评估、回归测试和回放调试。

### 功能点

| 编号 | 功能 | 优先级 |
|---|---|---|
| EVAL-001 | Replay Engine | P1 |
| EVAL-002 | Trajectory Evaluation | P1 |
| EVAL-003 | Tool Call Evaluation | P1 |
| EVAL-004 | Final Answer Evaluation | P1 |
| EVAL-005 | Safety Evaluation | P2 |
| EVAL-006 | Regression Dataset | P1 |
| EVAL-007 | Scorers | P1 |
| EVAL-008 | Eval Report | P2 |

---

## 7.24 Experiments

### 需求说明

Experiments 支持 Prompt、Model、Routing、Memory Policy、Tool Selection 的 A/B 测试和灰度实验。

### 功能点

| 编号 | 功能 | 优先级 |
|---|---|---|
| EXP-001 | Experiment Definition | P2 |
| EXP-002 | Variant Assignment | P2 |
| EXP-003 | Metrics Collection | P2 |
| EXP-004 | Rollout Policy | P2 |
| EXP-005 | Experiment Analysis | P3 |

---

## 7.25 Notifications

### 需求说明

Notifications 负责审批通知、任务完成通知、失败告警和外部回调。

### 功能点

| 编号 | 功能 | 优先级 |
|---|---|---|
| NTF-001 | Webhook Notification | P1 |
| NTF-002 | In-app Notification | P2 |
| NTF-003 | Slack Notification | P2 |
| NTF-004 | Email Notification | P2 |
| NTF-005 | Retry Delivery | P1 |
| NTF-006 | Subscription | P2 |

---

## 7.26 Control Plane

### 需求说明

Control Plane 负责平台资源管理。

### 功能点

| 编号 | 功能 | 优先级 |
|---|---|---|
| CP-001 | Agent Management | P1 |
| CP-002 | Skill Management | P1 |
| CP-003 | Tool Management | P1 |
| CP-004 | Prompt Management | P1 |
| CP-005 | Policy Management | P1 |
| CP-006 | Memory Management | P2 |
| CP-007 | Eval Management | P2 |
| CP-008 | Deployment Management | P2 |

---

## 7.27 Deployment

### 需求说明

Deployment 管理 Agent、Skill、Prompt、Tool、Policy 的版本、发布、回滚和环境。

### 功能点

| 编号 | 功能 | 优先级 |
|---|---|---|
| DEP-001 | Deployment Manifest | P1 |
| DEP-002 | Release Version | P1 |
| DEP-003 | Environment Binding | P1 |
| DEP-004 | Rollout | P2 |
| DEP-005 | Rollback | P2 |
| DEP-006 | Lockfile | P2 |

---

## 8. 非功能需求

## 8.1 性能需求

| 指标 | MVP 目标 | 生产目标 |
|---|---:|---:|
| API 创建任务延迟 | < 300ms | < 100ms |
| Runtime step 调度延迟 | < 500ms | < 100ms |
| Tool 执行调度延迟 | < 1s | < 300ms |
| Event 写入延迟 | < 100ms | < 30ms |
| Replay 查询首包 | < 3s | < 1s |
| 单任务最大 step | 50 | 可配置 |
| 单任务最大运行时间 | 30 分钟 | 可配置 |

## 8.2 可用性需求

- API Server 支持水平扩展。
- Worker 支持水平扩展。
- Event Store 不允许丢事件。
- Tool Execution 支持失败重试。
- Memory 写入失败不应导致主任务直接失败，除非该任务显式依赖记忆写入。
- Observability 失败不应阻断主链路。

## 8.3 安全需求

- 所有请求必须绑定 tenant_id。
- Tool 调用必须校验 scope。
- 高风险工具必须可配置人工审批。
- Sandbox 默认无网络。
- VFS 默认只能访问任务 workspace。
- Secret 不能出现在 Prompt 明文、日志、Event payload 中。
- Memory 写入必须经过 policy。
- 跨租户 memory、artifact、vfs、event 严禁访问。

## 8.4 可观测需求

- 每个任务必须有 trace_id。
- 每次模型调用必须记录 model、tokens、latency、cost、status。
- 每次工具调用必须记录 tool_name、risk_level、latency、status、sandbox_id。
- 每次 memory 写入必须记录 source、type、confidence、policy_decision。
- 每次 artifact 创建必须记录 lineage。

## 8.5 可测试需求

- 核心模块单测覆盖率 >= 80%。
- Runtime、Tool、Memory、Policy、Prompt Engine 单测覆盖率 >= 90%。
- 所有内置 Skill 必须有 eval dataset。
- 所有内置 Prompt 必须有 schema validation。
- 每个 release 必须通过 regression eval。

---

## 9. 数据模型概览

### 9.1 核心实体

```text
Tenant
User
Project
Session
AgentRun
AgentRunStep
Task
RuntimeEvent
Agent
AgentCard
Skill
SkillVersion
PromptTemplate
PromptVersion
ToolDefinition
ToolCall
MemoryItem
KnowledgeDocument
Artifact
PolicyRule
ApprovalRequest
EvaluationRun
DeploymentRelease
```

### 9.2 AgentRun

```python
class AgentRun(BaseModel):
    id: str
    tenant_id: str
    project_id: str | None
    session_id: str | None
    created_by: str
    input_message_id: str | None
    status: AgentRunStatus
    mode: str
    requested_pattern: str | None
    active_pattern: str | None
    context_message_sequence: int | None
    finish_reason: str | None
    max_steps: int
    deadline_at: datetime | None
    cost_budget: Decimal | None
    trace_id: str
    created_at: datetime
    updated_at: datetime
```

`Task` 保留为后续 planning/todo/reminder/markdown plan 引擎的领域对象；当前 Agent runtime、Session 与 Pattern 交付不依赖 Task 或 TaskStep 持久化。

### 9.3 RuntimeEvent

```python
class RuntimeEvent(BaseModel):
    event_id: str
    event_type: str
    event_version: str
    tenant_id: str
    agent_run_id: str
    session_id: str | None
    trace_id: str
    span_id: str
    parent_span_id: str | None
    actor_type: str
    actor_id: str | None
    payload: dict[str, Any]
    created_at: datetime
```

### 9.4 ToolDefinition

```python
class ToolDefinition(BaseModel):
    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any] | None
    category: str
    risk_level: Literal["low", "medium", "high", "critical"]
    requires_approval: bool
    scopes: list[str]
    timeout_ms: int
    retryable: bool
    idempotent: bool
    sandbox_required: bool
```

### 9.5 MemoryItem

```python
class MemoryItem(BaseModel):
    id: str
    tenant_id: str
    project_id: str | None
    user_id: str | None
    memory_type: Literal["summary", "semantic", "entity", "episodic"]
    content: str
    metadata: dict[str, Any]
    confidence: float
    source_agent_run_id: str | None
    visibility_scope: str
    created_at: datetime
    updated_at: datetime
```

---

## 10. API 需求概览

### 10.1 AgentRun API

```text
POST   /v1/agent-runs
GET    /v1/agent-runs/{agent_run_id}
GET    /v1/agent-runs/{agent_run_id}/events
GET    /v1/agent-runs/{agent_run_id}/stream
POST   /v1/agent-runs/{agent_run_id}/cancel
POST   /v1/agent-runs/{agent_run_id}/replay
```

### 10.2 Session API

```text
POST   /v1/sessions
GET    /v1/sessions/{session_id}
GET    /v1/sessions/{session_id}/history
POST   /v1/sessions/{session_id}/compact
```

### 10.3 Agent API

```text
GET    /v1/agents
POST   /v1/agents
GET    /v1/agents/{agent_id}
PUT    /v1/agents/{agent_id}
```

### 10.4 Skill API

```text
GET    /v1/skills
POST   /v1/skills/install
GET    /v1/skills/{skill_id}
GET    /v1/skills/{skill_id}/versions
```

### 10.5 Tool API

```text
GET    /v1/tools
POST   /v1/tools/register
GET    /v1/tools/{tool_name}
POST   /v1/tools/{tool_name}/test
```

### 10.6 Memory API

```text
GET    /v1/memory/search
POST   /v1/memory
PATCH  /v1/memory/{memory_id}
DELETE /v1/memory/{memory_id}
```

### 10.7 Artifact API

```text
GET    /v1/artifacts
GET    /v1/artifacts/{artifact_id}
GET    /v1/artifacts/{artifact_id}/download
GET    /v1/artifacts/{artifact_id}/preview
```

### 10.8 Evaluation API

```text
POST   /v1/evals/run
GET    /v1/evals/{eval_run_id}
GET    /v1/evals/{eval_run_id}/report
```

---

## 11. MVP 范围

## 11.1 MVP 必须包含

| 模块 | 能力 |
|---|---|
| access | API + CLI 接入 |
| identity | API Key + tenant_id + basic RBAC |
| runtime | AgentRun 创建、事件循环、step runner、流式输出 |
| events | Event Store + basic replay data |
| models | OpenAI + mock adapter + model selector |
| prompts | Prompt registry + renderer + output schema |
| skills | 本地 skill.yaml loader |
| hooks | before/after model/tool/memory hooks |
| patterns | single_turn、chaining、routing、planning、react、reflection 与 selector |
| tools | registry、executor、schema validation |
| context | context assembler + token budget |
| memory | session、working、summary memory |
| vfs | local workspace/artifacts |
| governance | tool risk guard、audit、approval stub |
| observability | trace、token、cost、latency |
| storage | Postgres + Redis + local object store |
| workers | runtime worker + tool worker |

## 11.2 MVP 不包含

- 完整 marketplace。
- Firecracker sandbox。
- 完整 A2A 外部协议。
- 复杂 ABAC。
- 多模型自动优化实验。
- Web 管理控制台完整 UI。
- 多租户计费。
- 高级 episodic memory。

---

## 12. 迭代路线

### Phase 0：架构打底

周期：1-2 周

交付：

- Monorepo 初始化。
- pyproject.toml。
- contracts 基础 schema。
- storage 基础连接。
- API skeleton。
- CLI skeleton。

### Phase 1：单 Agent Runtime MVP

周期：4-6 周

交付：

- Runtime event loop。
- Model adapter。
- Prompt engine 基础版。
- Tool registry/executor。
- Context manager。
- Event store。
- Basic memory。
- Local VFS。
- Trace/cost logging。

### Phase 2：Skill + Hook + Pattern

周期：4-6 周

交付：

- Skill Engine。
- Hook Engine。
- Chaining / Routing / Planning。
- Tool policy。
- HITL stub。
- Summary memory。
- Replay viewer API。

### Phase 3：Multi-Agent + Workflow + Sandbox

周期：6-8 周

交付：

- Supervisor Agent。
- Ephemeral Subagent。
- Workflow engine。
- Docker sandbox。
- Result aggregation。
- Context isolation。
- Builtin research/coding/data agents。

### Phase 4：Knowledge + RAG + Evaluation

周期：6-8 周

交付：

- Knowledge ingestion。
- Vector retrieval。
- Citation。
- Semantic/entity memory。
- Eval runner。
- Regression dataset。
- Trajectory eval。

### Phase 5：Platformization

周期：8-12 周

交付：

- Control plane。
- Deployment versioning。
- Policy language。
- Notifications。
- Experiments。
- Production governance。
- Multi-tenant hardening。

---

## 13. 验收标准

## 13.1 MVP 验收

| 编号 | 验收项 | 通过标准 |
|---|---|---|
| AC-001 | 创建执行 | API 能创建 agent run 并返回 agent_run_id。 |
| AC-002 | 执行模型调用 | Runtime 能调用模型并返回最终响应。 |
| AC-003 | 工具调用 | Agent 能调用至少 3 个内置工具。 |
| AC-004 | Prompt 渲染 | Prompt 支持变量、schema、模型格式化。 |
| AC-005 | Skill 加载 | 能加载本地 skill.yaml 并限制工具范围。 |
| AC-006 | Hook 执行 | before_tool_call 可阻断高风险工具。 |
| AC-007 | Event 记录 | 每个 step 都有 RuntimeEvent。 |
| AC-008 | Trace 记录 | 每个 agent run 有 trace_id 和 cost/token 统计。 |
| AC-009 | Memory 写入 | Summary memory 可写入、检索。 |
| AC-010 | VFS 保存产物 | Agent 生成物能保存到 /artifacts。 |
| AC-011 | Replay | 能按 agent_run_id 查询事件轨迹。 |
| AC-012 | CLI | CLI 能运行一次本地 agent run。 |

## 13.2 质量验收

- 单元测试覆盖率 >= 80%。
- Runtime 核心测试覆盖率 >= 90%。
- Tool policy 测试覆盖率 >= 90%。
- Prompt schema validation 通过率 100%。
- 内置 demo agent run 成功率 >= 90%。
- 关键链路 trace 完整率 100%。

---

## 14. 成功指标

| 指标 | MVP 目标 | 生产目标 |
|---|---:|---:|
| 单 Agent 任务成功率 | >= 85% | >= 95% |
| Tool 调用 schema 合法率 | >= 95% | >= 99% |
| 高风险工具拦截率 | 100% | 100% |
| Runtime 崩溃恢复能力 | 基础 checkpoint | 完整 replay/resume |
| Prompt 渲染错误率 | < 3% | < 0.5% |
| Memory 错误写入率 | 人工抽检 | 策略+评估约束 |
| Trace 完整率 | 100% | 100% |
| 回归评估覆盖内置 Skill | >= 50% | >= 100% |

---

## 15. 主要风险与应对

| 风险 | 说明 | 应对 |
|---|---|---|
| 架构过大 | 模块过多，早期实现复杂 | MVP 收敛到 runtime/model/prompt/tool/context/memory/events。 |
| Agent Loop 失控 | 无限调用模型或工具 | max_steps、timeout、budget、cancellation。 |
| 工具风险 | Shell、文件、网络操作危险 | Tool policy、HITL、Sandbox、VFS scope。 |
| Memory 污染 | 错误记忆长期保存 | Memory candidate、confidence、policy、human review。 |
| 多智能体复杂 | 上下文污染、结果冲突 | Subagent isolation、structured result、Supervisor merge。 |
| Debug 困难 | 任务失败难复现 | Event sourcing、trace、replay。 |
| 成本失控 | 并行、反思、长上下文导致 token 激增 | token budget、cost tracking、model selector。 |
| Prompt 漂移 | Prompt 无版本导致线上不稳定 | Prompt versioning、deployment lockfile、eval regression。 |
| 插件安全 | 第三方 tool/skill/hook 风险 | plugin manifest、signature、allowlist、sandbox。 |

---

## 16. Open Questions

1. 首个目标场景优先选研究报告、代码审查，还是数据分析？
2. MVP 是否需要 Web UI，还是 API + CLI 即可？
3. 第一版模型是否只支持 OpenAI + mock，还是同时接 Claude/Gemini？
4. Sandbox 第一版采用 Docker 还是仅开发环境 subprocess？
5. Memory 第一版是否需要向量库，还是先做 summary memory？
6. 是否需要在第一版支持 MCP server/client？
7. 是否需要支持外部 A2A 协议，还是先做内部 multi-agent protocol？
8. 是否需要多租户生产隔离，还是先做单租户平台？
9. Prompt、Skill、Policy 的版本发布是否第一版纳入 deployment？
10. Eval 是否作为 MVP 阻塞项，还是 Phase 4 引入？

---

## 17. 推荐第一版技术栈

| 类别 | 推荐 |
|---|---|
| 语言 | Python 3.12+ |
| 包管理 | uv |
| API | FastAPI |
| Schema | Pydantic v2 |
| DB | PostgreSQL |
| ORM | SQLAlchemy 2.x |
| Migration | Alembic |
| Cache/Queue | Redis |
| Async Task | Celery / Dramatiq / Arq，MVP 可先用 asyncio worker |
| Object Store | Local FS，后续 S3/MinIO |
| Vector Store | 后续 Qdrant / pgvector |
| Observability | OpenTelemetry + Prometheus |
| CLI | Typer / Rich |
| Testing | pytest + pytest-asyncio |
| Sandbox | MVP subprocess dev-only，Phase 3 Docker |
| Config | pydantic-settings + YAML |

---

## 18. 推荐 MVP 目录裁剪

完整目录可以保留，但 MVP 优先实现以下目录：

```text
src/agent_platform/
├── access/
├── identity/
├── api/
├── cli/
├── core/
├── contracts/
├── runtime/
├── events/
├── tasks/
├── sessions/
├── models/
├── prompts/
├── skills/
├── hooks/
├── patterns/
├── tools/
├── context/
├── memory/
├── vfs/
├── governance/
├── observability/
├── storage/
└── workers/
```

Phase 2 后再重点实现：

```text
workflow/
agents/
multi_agent/
connectors/
sandbox/
evaluation/
```

Phase 3 后实现：

```text
knowledge/
rag/
artifacts/
policy/
experiments/
notifications/
control_plane/
deployment/
plugins/
```

---

## 19. 总结

该产品的核心不是构建一个简单 Agent SDK，而是构建一个完整的 Agent Platform。

平台核心设计原则：

```text
Runtime 负责执行生命周期
Events 负责事实记录与回放
Prompts 负责语言模板编译
Skills 负责能力组合复用
Hooks 负责生命周期扩展
Patterns 负责智能行为模式
Workflow 负责确定性流程
Agents 负责执行主体
Multi-Agent 负责协作结构
Tools 负责原子行动
Connectors 负责外部系统连接
Memory 负责长期状态
Knowledge/RAG 负责知识增强
VFS/Artifacts 负责文件和产物边界
Policy/Governance 负责安全治理
Evaluation 负责质量闭环
Deployment 负责版本上线
```

最终产品应具备以下特征：

```text
Pattern-driven
Runtime-driven
Multi-agent-native
Tool-governed
Memory-aware
Prompt-versioned
Skill-composable
Hook-extensible
Event-sourced
Replayable
Auditable
Evaluable
Deployable
Model-agnostic
```

这是一个可以长期演进为企业级 AI Agent 基础设施的平台型产品。
