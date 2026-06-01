# 自研 Agent Platform 低层设计文档（LLD）

版本：v0.1  
状态：Draft  
目标实现语言：Python 3.12+  
目标版本：MVP  
产品基线：PRD v0.1  
产品定位：通用 Agent Platform，API + CLI 首发，单租户，支持 OpenAI + Mock，支持 MCP 与 A2A，开发期 subprocess sandbox，先实现 Summary Memory，暂不将 Eval 作为 MVP 阻塞项。

---

## 1. LLD 范围

本文档定义 MVP 阶段的低层设计，覆盖：

1. 模块职责与包结构。
2. 核心类、接口与协议。
3. Runtime 执行流程。
4. Prompt / Skill / Hook / Tool / Memory / MCP / A2A 的实现细节。
5. API 与 CLI 设计。
6. 存储模型。
7. 配置结构。
8. 关键伪代码。
9. MVP 交付边界。

---

## 2. MVP 决策基线

| 问题 | 决策 |
|---|---|
| 首个目标场景 | 通用 Agent，不限定研究报告、代码审查或数据分析 |
| 交互形态 | API + CLI，不做 Web UI |
| 第一版模型 | OpenAI + Mock |
| Sandbox | 开发环境 subprocess runner |
| Memory | 先做 Summary Memory，不接向量库 |
| MCP | 第一版支持 MCP server/client |
| A2A | 第一版支持 A2A 协议能力 |
| 租户模式 | 单租户平台，暂不做多租户隔离 |
| Deployment | Prompt、Skill、Policy 版本发布纳入第一版 |
| Eval | 第一版先不做 Eval 阻塞项，仅保留扩展接口 |
| Runtime 执行单元 | `AgentRun`，公开关联键为 `agent_run_id` |
| Task 语义 | 保留为后续 planning/todo/reminder/markdown plan 引擎，不承担 AgentRun 生命周期 |
| 数据库代码归口 | ORM base/types、ORM records、repositories、SQLAlchemy session 统一放在 `src/storage/database/` |

**术语优先规则：** 本文历史版本曾使用 `Task` 表示 runtime 执行单元。从本决策起，运行状态机、事件关联、模型/工具调用来源、API 执行资源和 replay 上下文均以 `AgentRun` / `agent_run_id` 表达；仅规划待办领域使用 `Task`。未在本轮展开的远期章节若仍出现旧执行含义的 `task`，应按本规则解释并在对应能力落地前修订。

---

## 3. MVP 总体架构

### 3.1 分层架构

```text
API / CLI
  ↓
Access / Identity
  ↓
Runtime Kernel
  ↓
Skill Engine / Prompt Engine / Hook Engine / Pattern Engine
  ↓
Agent / Multi-Agent
  ↓
Tool Router / MCP / A2A / Sandbox
  ↓
Context / Summary Memory / VFS
  ↓
Storage / Events / Observability / Deployment
```

### 3.2 MVP 核心闭环

```text
User Request
→ Access Normalize
→ Identity Resolve
→ Runtime Create AgentRun
→ Skill Resolve
→ Context Assemble
→ Prompt Render
→ Model Invoke
→ Tool / MCP / A2A Dispatch
→ Observation Append
→ Summary Memory Update
→ Artifact Persist
→ Event Store
→ Final Response
```

### 3.3 MVP 不实现或弱实现

| 模块 | MVP 处理方式 |
|---|---|
| knowledge / rag | 保留目录，暂不实现完整知识库和向量检索 |
| evaluation / experiments | 保留接口，不作为阻塞项 |
| sandbox docker/firecracker | 不实现，仅 subprocess runner |
| multi-tenant isolation | 不实现，使用 default tenant |
| web console | 不实现 |
| complex workflow compensation | 不实现，仅基础 DAG/linear workflow |
| semantic/entity/episodic memory | 不实现，仅 summary memory |

---

## 4. 目标目录结构与 MVP 实现级别

```text
src/agent_platform/
├── access/              # P0：请求归一化、AccessContext
├── identity/            # P0：单租户、API Key、本地用户上下文
├── api/                 # P0：FastAPI HTTP 接口
├── cli/                 # P0：Typer CLI
├── core/                # P0：公共工具、异常、ID、时间、Result
├── contracts/           # P0：跨模块 Pydantic Schema
├── runtime/             # P0：运行时内核、事件循环、状态机、Step Runner
├── events/              # P0：Event Sourcing、Event Store、Event Bus 入口
├── agent_runs/          # P0：AgentRun、AgentRunStep 业务状态管理
├── tasks/               # P1：规划待办引擎预留，不属于当前 runtime 交付
├── sessions/            # P0：Session、history、summary compaction 业务管理
├── scheduler/           # P1：后台调度，MVP 仅保留接口
├── models/              # P0：OpenAI + Mock Adapter
├── prompts/             # P0：Prompt Registry、Renderer、Formatter、Versioning
├── skills/              # P0：Skill Manifest、Registry、Loader、Resolver
├── hooks/               # P0：Hook Manager、内置治理 hooks
├── patterns/            # P0：single_turn、chaining、routing、planning、react、reflection 与 selector
├── workflow/            # P1：linear / DAG workflow runner 基础版
├── agents/              # P0：BaseAgent、GeneralAgent、SupervisorAgent 基础版
├── multi_agent/         # P1：Subagent、A2A 基础支持
├── tools/               # P0：Tool Registry、Router、Executor、MCP Adapter
├── connectors/          # P1：HTTP / filesystem / MCP connector 基础实现
├── context/             # P0：Context Assembler、Token Budget、Observation Formatter
├── memory/              # P0：Summary Memory
├── knowledge/           # P2：保留目录
├── rag/                 # P2：保留目录
├── vfs/                 # P0：local workspace / artifacts / memories
├── artifacts/           # P1：Artifact metadata 基础版
├── sandbox/             # P0：subprocess runner，仅开发环境
├── policy/              # P0：基础 Policy Engine，Tool/Skill/Prompt Policy
├── governance/          # P0：Audit、risk guard、approval stub
├── observability/       # P0：logging、trace_id、token/cost 基础统计
├── evaluation/          # P2：保留接口
├── experiments/         # P2：保留接口
├── notifications/       # P1：Webhook notification stub
├── control_plane/       # P1：Prompt/Skill/Policy 管理 API 基础版
├── deployment/          # P0：Prompt/Skill/Policy version binding
├── storage/             # P0：SQLite/PostgreSQL Repository、ORM Model、DB session；Redis 可选
├── workers/             # P1：asyncio worker 基础版
└── plugins/             # P1：插件 manifest 与本地 loader
```

---

## 5. 核心数据契约设计

所有跨模块 Schema 优先放在 `contracts/`，模块内部可有私有 schema，但外部交互必须使用 contracts。

### 5.1 `contracts/runtime/messages.py`

```python
from typing import Any, Literal
from pydantic import BaseModel, Field

MessageRole = Literal["system", "user", "assistant", "tool"]

class Message(BaseModel):
    role: MessageRole
    content: str | list[dict[str, Any]]
    name: str | None = None
    tool_call_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
```

### 5.2 `contracts/requests.py`

```python
from typing import Any, Literal
from pydantic import BaseModel, Field

Channel = Literal["api", "cli", "webhook", "a2a", "mcp"]

class AgentRequest(BaseModel):
    request_id: str
    channel: Channel
    user_id: str = "local-user"
    tenant_id: str = "default"
    project_id: str = "default"
    session_id: str | None = None
    goal: str
    input: dict[str, Any] = Field(default_factory=dict)
    constraints: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
```

### 5.3 `contracts/agent_runs.py`

```python
from typing import Any, Literal
from datetime import datetime
from pydantic import BaseModel, Field

AgentRunStatus = Literal["created", "running", "completed", "failed", "cancelled"]
AgentRunStepKind = Literal[
    "pattern_selection", "pattern_transition", "model_invocation",
    "tool_execution", "finalization", "agent", "workflow", "human", "system"
]
AgentRunStepStatus = Literal["pending", "running", "completed", "failed", "cancelled", "skipped"]

class AgentRun(BaseModel):
    agent_run_id: str
    session_id: str | None = None
    input_message_id: str | None = None
    mode: Literal["chat", "plan", "build", "review"] = "chat"
    requested_pattern: str | None = None
    active_pattern: str | None = None
    status: AgentRunStatus = "created"
    context_message_sequence: int | None = None
    trace_id: str
    finish_reason: str | None = None
    error_type: str | None = None
    max_steps: int = 30
    timeout_seconds: int = 600
    cost_budget_usd: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

class AgentRunStep(BaseModel):
    step_id: str
    agent_run_id: str
    index: int
    kind: AgentRunStepKind
    status: AgentRunStepStatus = "pending"
    pattern: str | None = None
    invocation_id: str | None = None
    input: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    created_at: datetime
    updated_at: datetime
```

### 5.4 `contracts/runtime/events.py`

```python
class RuntimeEventType(StrEnum):
    MODEL_INVOCATION_STARTED = "model_invocation_started"
    MODEL_INVOCATION_COMPLETED = "model_invocation_completed"
    MODEL_INVOCATION_FAILED = "model_invocation_failed"
    MODEL_TOOL_CALLS_PRODUCED = "model_tool_calls_produced"

class RuntimeEvent(BaseModel):
    event_id: str
    event_type: RuntimeEventType
    event_version: int = 1
    agent_run_id: str | None = None
    step_id: str | None = None
    session_id: str | None = None
    trace_id: str
    span_id: str
    parent_span_id: str | None = None
    actor_type: Literal["runtime", "system", "user"]
    actor_id: str | None = None
    payload: (
        ModelInvocationStartedPayload
        | ModelInvocationCompletedPayload
        | ModelInvocationFailedPayload
        | ModelToolCallsProducedPayload
    )
    created_at: datetime
```

生命周期 payload 仅保存 invocation 身份、provider/model/protocol、状态、usage、
latency、错误决策字段与工具名称等安全事实。完成事件不复制模型正文或 raw wire
body，工具意图事件不保存完整 arguments。实时文本和工具参数增量属于
`ModelStreamEvent`，不要求逐 delta 形成 durable `RuntimeEvent`。

### 5.5 `contracts/runtime/models.py`

```python
from typing import Any, Literal
from pydantic import BaseModel, Field
from .messages import Message

class ModelCapabilities(BaseModel):
    tool_calling: bool = False
    json_schema: bool = False
    streaming: bool = False
    vision: bool = False
    reasoning: bool = False

class ModelRequest(BaseModel):
    invocation_id: str
    provider: str | None = None
    model: str
    protocol: Literal["openai_chat", "openai_responses", "anthropic_messages", "custom", "mock"] | None = None
    messages: list[Message]
    options: ModelOptions = Field(default_factory=ModelOptions)
    tools: list[dict[str, Any]] = Field(default_factory=list)
    response_format: dict[str, Any] | None = None
    stream: bool = False
    timeout_seconds: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

class ToolCall(BaseModel):
    id: str
    name: str
    arguments: dict[str, Any]

class ModelUsage(BaseModel):
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    cached_input_tokens: int | None = None
    cache_creation_input_tokens: int | None = None
    reasoning_tokens: int | None = None

class ModelResponse(BaseModel):
    invocation_id: str
    provider: str
    model: str
    protocol: str
    content: list[ModelContentBlock] = Field(default_factory=list)
    tool_calls: list[ToolCall] = Field(default_factory=list)
    status: Literal["completed", "incomplete", "refused"]
    stop_reason: Literal["completed", "tool_use", "max_tokens", "content_filtered", "refused", "unknown"]
    provider_stop_reason: str | None = None
    usage: ModelUsage | None = None
```

### 5.6 `contracts/tools.py`

```python
from typing import Any, Literal
from pydantic import BaseModel, Field

RiskLevel = Literal["low", "medium", "high", "critical"]
ToolCategory = Literal["function", "filesystem", "http", "shell", "python", "mcp", "a2a", "custom"]

class ToolDefinition(BaseModel):
    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any] | None = None
    category: ToolCategory = "function"
    risk_level: RiskLevel = "low"
    requires_approval: bool = False
    scopes: list[str] = Field(default_factory=list)
    timeout_seconds: int = 30
    retryable: bool = False
    idempotent: bool = False
    sandbox_required: bool = False
    enabled: bool = True

class ToolInvocation(BaseModel):
    invocation_id: str
    agent_run_id: str
    tool_name: str
    arguments: dict[str, Any]
    approved: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)

class ToolResult(BaseModel):
    invocation_id: str
    tool_name: str
    ok: bool
    content: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    artifacts: list[str] = Field(default_factory=list)
```

### 5.7 `contracts/skills.py`

```python
from typing import Any, Literal
from pydantic import BaseModel, Field

class SkillPromptRefs(BaseModel):
    system: str | None = None
    entry: str
    reflection: str | None = None
    summarizer: str | None = None

class SkillTools(BaseModel):
    allowed: list[str] = Field(default_factory=list)
    denied: list[str] = Field(default_factory=list)

class SkillMemoryPolicy(BaseModel):
    read: list[str] = Field(default_factory=list)
    write_mode: Literal["none", "summary_only", "propose"] = "summary_only"

class SkillManifest(BaseModel):
    name: str
    version: str
    description: str | None = None
    type: Literal["general", "composite", "workflow"] = "general"
    prompts: SkillPromptRefs
    tools: SkillTools = Field(default_factory=SkillTools)
    patterns: list[str] = Field(default_factory=list)
    workflow: str | None = None
    memory: SkillMemoryPolicy = Field(default_factory=SkillMemoryPolicy)
    policy: dict[str, Any] = Field(default_factory=dict)
    hooks: dict[str, list[str]] = Field(default_factory=dict)
    output_schema: str | None = None
```

### 5.8 `contracts/prompts.py`

```python
from typing import Any, Literal
from pydantic import BaseModel, Field

class PromptVariable(BaseModel):
    name: str
    type: str = "string"
    required: bool = True
    source: str | None = None
    default: Any | None = None

class PromptTemplateSpec(BaseModel):
    name: str
    version: str
    description: str | None = None
    type: Literal["chat", "text"] = "chat"
    templates: dict[str, str]
    variables: list[PromptVariable] = Field(default_factory=list)
    output_schema: str | None = None
    model_compatibility: list[str] = Field(default_factory=list)
    policy: dict[str, Any] = Field(default_factory=dict)
```

### 5.9 `contracts/hooks.py`

```python
from typing import Any, Literal
from pydantic import BaseModel, Field

HookAction = Literal["continue", "modify", "block"]

class HookContext(BaseModel):
    hook_name: str
    agent_run_id: str | None = None
    session_id: str | None = None
    agent_id: str | None = None
    skill_id: str | None = None
    tool_name: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

class HookResult(BaseModel):
    action: HookAction = "continue"
    payload: dict[str, Any] | None = None
    reason: str | None = None
```

### 5.10 `contracts/memory.py`

```python
from typing import Any, Literal
from datetime import datetime
from pydantic import BaseModel, Field

MemoryType = Literal["summary"]

class MemoryItem(BaseModel):
    memory_id: str
    session_id: str | None = None
    source_agent_run_id: str | None = None
    type: MemoryType = "summary"
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
```

---

## 6. Runtime 低层设计

## 6.1 Runtime 目录结构

```text
runtime/
├── __init__.py
├── kernel.py              # AgentRuntimeKernel 主入口
├── event_loop.py          # Runtime 主循环
├── dispatcher.py          # 事件/步骤分发
├── scheduler.py           # step 调度，区别于平台级 scheduler/
├── step_runner.py         # 执行 model/tool/agent/workflow step
├── state_machine.py       # AgentRun 生命周期状态机
├── cancellation.py        # 取消控制
├── checkpoint.py          # checkpoint 保存/恢复
├── replay.py              # replay 基础逻辑
├── context.py             # RuntimeContext
├── lifecycle.py           # 生命周期管理
├── hooks.py               # runtime-hook 集成
├── schemas.py             # runtime 内部 schema
└── policies.py            # max_steps/timeout/budget 检查
```

## 6.2 RuntimeKernel 接口

```python
class AgentRuntimeKernel:
    def __init__(
        self,
        run_repo: AgentRunRepository,
        event_store: EventStore,
        session_manager: SessionManager,
        pattern_selector: PatternSelector,
        pattern_registry: PatternRegistry,
        model_registry: ModelRegistry,
        prompt_engine: PromptEngine,
        skill_engine: SkillEngine,
        hook_manager: HookManager,
        tool_router: ToolRouter,
        context_manager: ContextManager,
        memory_manager: MemoryManager,
        vfs: VFS,
        policy_engine: PolicyEngine,
        observer: Observer,
    ) -> None:
        ...

    async def start_run(self, request: AgentRequest) -> AgentRun:
        ...

    async def run_until_complete(self, agent_run_id: str) -> AgentRun:
        ...

    async def cancel_run(self, agent_run_id: str) -> None:
        ...

    async def get_run_state(self, agent_run_id: str) -> AgentRun:
        ...
```

## 6.3 Runtime 主循环伪代码

```python
async def run_until_complete(agent_run_id: str) -> AgentRun:
    run = await run_repo.get(agent_run_id)
    ctx = await runtime_context_builder.build(run)

    await hooks.dispatch("before_agent_run_start", ctx.to_hook_context())
    await events.append("AgentRunStarted", agent_run_id=run.agent_run_id)
    pattern = await pattern_selector.select(run, ctx)
    await events.append("PatternSelected", agent_run_id=run.agent_run_id, payload={"pattern": pattern.name})

    step_count = 0

    while run.status not in {"completed", "failed", "cancelled"}:
        step_count += 1

        if step_count > run.max_steps:
            await fail_run(run, "max_steps_exceeded")
            break

        if await cancellation.is_cancelled(run.agent_run_id):
            await cancel_run(run.agent_run_id)
            break

        await runtime_policy.check_timeout(run)
        await runtime_policy.check_budget(run)

        context_bundle = await context_manager.assemble(run)
        action = await pattern.next_action(run, context_bundle)

        if action.kind == "transition_pattern":
            pattern = await pattern_registry.require(action.pattern)
            await events.append("PatternTransitioned", agent_run_id=run.agent_run_id)
            continue
        if action.kind == "complete":
            await session_manager.append_final_response(run, action.response)
            run.status = "completed"
            await run_repo.save(run)
            break

        model_request = action.model_request
        model_request.metadata["agent_run_id"] = run.agent_run_id

        reducer = ModelStreamReducer()
        async for stream_event in model_registry.stream(model_request):
            reducer.consume(stream_event)
            await stream.forward_public_delta(stream_event)
        response = reducer.response()
        await events.append("ModelInvocationCompleted", agent_run_id=run.agent_run_id)

        if response.tool_calls:
            await pattern.accept_observation(response)
            continue

        await pattern.accept_observation(response)

    await hooks.dispatch("after_agent_run_complete", ctx.to_hook_context())
    return run
```

## 6.4 状态机转换

```text
created
  -> running
  -> completed

failed/cancelled 可从 running 转入。pattern 的 routing/planning/react/reflection 行为作为 step/event 表达，不属于顶层状态。
```

### 转换规则

| From | To | 触发条件 |
|---|---|---|
| created | running | start_run |
| running | completed | final response committed to session |
| any active | failed | unhandled exception / policy block |
| any active | cancelled | user/system cancel |

---

## 7. Access / Identity 设计

## 7.1 Access 模块

```text
access/
├── schemas.py
├── auth.py
├── tenant.py
├── request_normalizer.py
└── channels/
    ├── api.py
    ├── cli.py
    ├── webhook.py
    ├── a2a.py
    └── mcp.py
```

### AccessContext

```python
class AccessContext(BaseModel):
    user_id: str = "local-user"
    tenant_id: str = "default"
    project_id: str = "default"
    roles: list[str] = ["admin"]
    scopes: list[str] = ["*"]
    channel: str
    request_id: str
```

## 7.2 Identity MVP

MVP 为单租户：

```text
tenant_id = "default"
user_id = "local-user" 或从 API Key 解析
roles = ["admin"]
```

API Key 可通过 `.env` 配置：

```env
AGENT_PLATFORM_API_KEY=dev-key
```

---

## 8. API 低层设计

## 8.1 API 目录

```text
api/
├── app.py
├── dependencies.py
├── middleware.py
├── routers/
│   ├── health.py
│   ├── agent_runs.py
│   ├── sessions.py
│   ├── skills.py
│   ├── prompts.py
│   ├── tools.py
│   ├── memory.py
│   ├── mcp.py
│   └── a2a.py
└── schemas/
```

## 8.2 FastAPI App

```python
from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(title="Agent Platform", version="0.1.0")
    app.include_router(health.router, prefix="/health")
    app.include_router(agent_runs.router, prefix="/v1/agent-runs")
    app.include_router(sessions.router, prefix="/v1/sessions")
    app.include_router(skills.router, prefix="/v1/skills")
    app.include_router(prompts.router, prefix="/v1/prompts")
    app.include_router(tools.router, prefix="/v1/tools")
    app.include_router(memory.router, prefix="/v1/memory")
    app.include_router(mcp.router, prefix="/v1/mcp")
    app.include_router(a2a.router, prefix="/v1/a2a")
    return app
```

## 8.3 Endpoint 设计

### Agent Runs

```text
POST /v1/agent-runs
GET  /v1/agent-runs/{agent_run_id}
GET  /v1/agent-runs/{agent_run_id}/events
GET  /v1/agent-runs/{agent_run_id}/stream
POST /v1/agent-runs/{agent_run_id}/cancel
POST /v1/agent-runs/{agent_run_id}/replay
```

#### POST `/v1/agent-runs`

Request:

```json
{
  "goal": "帮我分析一下这个项目如何启动",
  "session_id": null,
  "input": {},
  "constraints": {
    "max_steps": 20,
    "timeout_seconds": 600
  }
}
```

Response:

```json
{
  "agent_run_id": "run_...",
  "status": "created"
}
```

### Sessions

```text
POST /v1/sessions
GET  /v1/sessions/{session_id}
GET  /v1/sessions/{session_id}/history
POST /v1/sessions/{session_id}/compact
```

### Skills

```text
GET  /v1/skills
GET  /v1/skills/{name}
POST /v1/skills/reload
```

### Prompts

```text
GET  /v1/prompts
GET  /v1/prompts/{name}
POST /v1/prompts/render
```

### Tools

```text
GET  /v1/tools
GET  /v1/tools/{name}
POST /v1/tools/{name}/invoke
```

### MCP

```text
GET  /v1/mcp/tools
POST /v1/mcp/tools/call
GET  /v1/mcp/resources
GET  /v1/mcp/prompts
```

### A2A

```text
GET  /v1/a2a/agent-card
POST /v1/a2a/tasks
GET  /v1/a2a/tasks/{task_id}
```

`A2A task` 是外部协议资源名称；进入平台后映射为内部 `AgentRun`，不得作为内部 runtime 主键语义复用。

---

## 9. CLI 低层设计

## 9.1 CLI 目录

```text
cli/
├── main.py
├── console.py
└── commands/
    ├── run.py
    ├── chat.py
    ├── replay.py
    ├── skills.py
    ├── prompts.py
    ├── tools.py
    ├── mcp.py
    └── a2a.py
```

## 9.2 命令设计

```bash
agent-platform run "帮我制定一个学习计划"
agent-platform chat
agent-platform replay run_123
agent-platform skills list
agent-platform prompts list
agent-platform prompts render planner.create_plan --var goal="..."
agent-platform tools list
agent-platform tools invoke calculator.add '{"a":1,"b":2}'
agent-platform mcp tools
agent-platform a2a card
```

## 9.3 CLI 主入口

```python
import typer

app = typer.Typer(name="agent-platform")

app.add_typer(run.app, name="run")
app.add_typer(chat.app, name="chat")
app.add_typer(replay.app, name="replay")
app.add_typer(skills.app, name="skills")
app.add_typer(prompts.app, name="prompts")
app.add_typer(tools.app, name="tools")
app.add_typer(mcp.app, name="mcp")
app.add_typer(a2a.app, name="a2a")
```

---

## 10. Model Adapter 设计

## 10.0 当前协议与事件边界

模型调用实现将 `provider`、`protocol` 与 `model profile` 分离：

| 边界 | 当前职责 |
|---|---|
| provider | endpoint、认证与 transport 配置 |
| protocol | wire payload、blocking/streaming 解析及错误映射 |
| model profile | 选择 protocol 并声明工具、streaming、结构化输出等能力 |

本变更覆盖 `openai_chat`、`openai_responses` 与无网络依赖的 Mock 路径。
`anthropic_messages` 只保留 protocol identity，未实现 Anthropic 网络调用；
未注册的 `custom` protocol 同样不可执行。

`ModelStreamEvent` 用于高频实时 delta 及流归约；`RuntimeEvent` 只描述开始、
完成、失败和工具意图等 durable lifecycle facts，并通过 `src.events` 提供发现入口。
正式平台错误入口为 `src.exceptions`，models 错误仅公开可供 runtime 判定的安全字段。

本变更明确不实现 Event Store/Event Bus/replay、Anthropic 调用、
pricing/cost budget 或自动 retry/fallback 策略。

## 10.1 目录

```text
models/
├── base.py
├── registry.py
├── selector.py
├── profiles.py
├── streaming.py
├── protocols/
│   ├── openai_chat.py
│   ├── openai_responses.py
│   ├── anthropic_messages.py  # reserved
│   └── custom.py              # registration boundary
└── providers/
    ├── openai.py
    └── mock.py
```

## 10.2 Base Adapter

```python
class ModelAdapter(Protocol):
    async def invoke(self, request: ModelRequest) -> ModelResponse:
        ...

    async def stream(self, request: ModelRequest) -> AsyncIterator[ModelStreamEvent]:
        ...
```

## 10.3 OpenAI Protocol Adapters

OpenAI provider 可按 profile 选择 `openai_chat` 或 `openai_responses`。两种
protocol 各自转换请求和解析流事件，最终均输出统一 `ModelResponse` /
`ModelStreamEvent`，不会向 runtime 暴露 provider wire body。

## 10.4 Mock Adapter

用于测试：

```python
class MockModelAdapter:
    name = "mock"

    async def invoke(self, request: ModelRequest) -> ModelResponse:
        if "tool" in request.metadata.get("mode", ""):
            return ModelResponse(tool_calls=[...])
        return ModelResponse(content="mock response")
```

## 10.5 Model Selector

选择规则：

```text
request.provider / request.model / request.protocol
    + provider registration
    + model profile
    -> protocol adapter + capability validation
```

模型能力不满足或 protocol 尚未注册时在发起 transport 前失败；models 层不执行
隐式 provider fallback。

---

## 11. Prompt Engine 设计

## 11.1 目录

```text
prompts/
├── engine.py
├── registry.py
├── loader.py
├── renderer.py
├── formatter.py
├── variables.py
├── resolver.py
├── versioning.py
├── validation.py
├── output/
│   ├── parser.py
│   ├── schema_binder.py
│   └── repair.py
├── formats/
│   ├── openai_chat.py
│   ├── anthropic_messages.py
│   └── plain_text.py
└── builtin/
    ├── general_agent/
    ├── planner/
    ├── router/
    └── summarizer/
```

## 11.2 PromptEngine 接口

```python
class PromptEngine:
    async def render(
        self,
        template_name: str,
        variables: dict[str, Any],
        model_provider: str,
        version: str | None = None,
    ) -> PromptRenderResult:
        ...

    async def render_for_run(
        self,
        run: AgentRun,
        skill: ResolvedSkill,
        context: ContextBundle,
    ) -> ModelRequest:
        ...
```

## 11.3 Prompt 渲染流程

```text
Resolve template name/version
→ Load prompt.yaml
→ Validate required variables
→ Resolve dynamic variables
→ Render markdown templates
→ Bind output schema
→ Format as model-specific messages
→ Run hooks before_prompt_send
→ Return ModelRequest
```

## 11.4 内置 General Agent Prompt

```text
prompts/builtin/general_agent/
├── prompt.yaml
├── system.md
├── entry.md
└── output.schema.json
```

`system.md`：

```text
你是一个通用任务智能体。

你可以：
1. 理解用户目标。
2. 拆解任务。
3. 在需要时调用工具。
4. 根据工具结果继续推理。
5. 输出清晰、可执行的最终结果。

约束：
- 不要编造工具结果。
- 调用工具前必须确保工具在 allowed_tools 中。
- 不要输出隐藏推理过程。
- 如果信息不足，提出澄清问题。
```

`entry.md`：

```text
用户目标：
<goal>
{{ goal }}
</goal>

当前上下文：
<context>
{{ context }}
</context>

可用工具：
<tools>
{{ tools }}
</tools>

历史摘要：
<memory_summary>
{{ memory_summary }}
</memory_summary>

请完成任务。
```

---

## 12. Skill Engine 设计

## 12.1 目录

```text
skills/
├── base.py
├── manifest.py
├── registry.py
├── loader.py
├── resolver.py
├── engine.py
├── executor.py
├── policy.py
├── runtime/
│   ├── skill_context.py
│   └── skill_state.py
└── builtin/
    └── general/
        ├── skill.yaml
        ├── prompts/
        ├── policies/
        └── schemas/
```

## 12.2 General Skill Manifest

```yaml
name: general
version: 0.1.0
description: General-purpose agent skill.
type: general

prompts:
  system: general_agent.system
  entry: general_agent.entry
  summarizer: summarizer.session_summary

tools:
  allowed:
    - builtin.echo
    - builtin.datetime
    - builtin.calculator
    - builtin.read_file
    - builtin.write_file
    - mcp.*
    - a2a.*
  denied:
    - builtin.shell

patterns:
  - routing
  - planning
  - chaining

memory:
  read:
    - summary
  write:
    mode: summary_only

policy:
  max_steps: 30
  require_tool_schema_validation: true

hooks:
  before_tool_call:
    - tool_risk_guard
  before_memory_write:
    - memory_write_guard
```

## 12.3 SkillResolver 逻辑

MVP 逻辑：

```text
1. 如果 request 显式指定 skill，则加载该 skill。
2. 否则默认使用 general@latest。
3. 根据 deployment lockfile 解析实际版本。
4. 返回 ResolvedSkill，包括 prompt refs、allowed tools、policy、hooks。
```

```python
class SkillResolver:
    async def resolve(self, run: AgentRun, context: ContextBundle) -> ResolvedSkill:
        skill_name = run.metadata.get("skill") or "general"
        version = self.deployment.resolve_skill_version(skill_name)
        manifest = await self.registry.get(skill_name, version)
        return ResolvedSkill.from_manifest(manifest)
```

---

## 13. Hook Engine 设计

## 13.1 目录

```text
hooks/
├── base.py
├── types.py
├── registry.py
├── manager.py
├── dispatcher.py
├── context.py
├── builtin/
│   ├── tracing.py
│   ├── audit.py
│   ├── cost_tracking.py
│   ├── prompt_injection_guard.py
│   ├── tool_risk_guard.py
│   └── memory_write_guard.py
└── lifecycle/
    ├── agent_run_hooks.py
    ├── model_hooks.py
    ├── tool_hooks.py
    ├── prompt_hooks.py
    └── memory_hooks.py
```

## 13.2 HookManager

```python
class HookManager:
    def __init__(self) -> None:
        self._hooks: dict[str, list[Hook]] = {}

    def register(self, hook_name: str, hook: Hook) -> None:
        self._hooks.setdefault(hook_name, []).append(hook)
        self._hooks[hook_name].sort(key=lambda h: h.priority)

    async def dispatch(self, hook_name: str, context: HookContext) -> HookContext:
        for hook in self._hooks.get(hook_name, []):
            result = await hook.run(context)
            if result.action == "block":
                raise HookBlockedError(hook_name, hook.name, result.reason)
            if result.action == "modify" and result.payload:
                context.payload.update(result.payload)
        return context
```

## 13.3 MVP Hook Points

```text
before_agent_run_start
after_agent_run_complete
on_agent_run_error
before_prompt_send
before_model_call
after_model_call
before_tool_call
after_tool_call
before_memory_write
after_memory_write
```

## 13.4 ToolRiskGuard

```python
class ToolRiskGuard:
    name = "tool_risk_guard"
    priority = 10

    async def run(self, context: HookContext) -> HookResult:
        tool_def = context.payload["tool_definition"]
        if tool_def["risk_level"] in {"high", "critical"}:
            return HookResult(action="block", reason="high risk tool blocked in MVP")
        return HookResult(action="continue")
```

---

## 14. Pattern Engine 设计

## 14.1 MVP 实现模式

| Pattern | MVP 实现 |
|---|---|
| Single Turn | 直接完成单次用户请求的基线策略 |
| Prompt Chaining | Linear chain runner |
| Routing | Rule + LLM router，允许选择/切换 pattern |
| Planning | 规划推理与输出策略；不创建持久化 Task |
| ReAct | Model/action/observation 循环，工具 action 通过 runtime 执行 |
| Reflection | Critic/Verifier/Reviser 路径 |
| Parallelization | 暂不实现，保留接口 |

## 14.2 目录

```text
patterns/
├── base.py
├── registry.py
├── selector.py
├── modes.py
├── single_turn/
│   └── pattern.py
├── chaining/
│   ├── chain.py
│   └── runner.py
├── routing/
│   ├── router.py
│   ├── rule_router.py
│   └── llm_router.py
├── planning/
│   ├── planner.py
│   └── schemas.py
├── react/
│   ├── pattern.py
│   └── schemas.py
└── reflection/
    ├── critic.py
    └── verifier.py
```

## 14.3 Pattern 与 Task Engine 边界

```text
PlanningPattern
  -> 本阶段：生成或推进规划型 AgentRun 行为
  -> 后续 v1 Task Engine：内存 todo + reminder
  -> 后续 v2 Task Engine：磁盘 Markdown plan
```

当前 runtime/session/pattern 变更不得以 Task 持久化、reminder 或 Markdown plan 作为验收条件。

---

## 15. Agent / Multi-Agent / A2A 设计

## 15.1 Agents 目录

```text
agents/
├── base.py
├── card.py
├── registry.py
├── factory.py
├── general_agent.py
├── supervisor.py
└── worker.py
```

## 15.2 BaseAgent

```python
class BaseAgent(Protocol):
    agent_id: str
    name: str
    description: str

    async def run(self, run: AgentRun, context: ContextBundle) -> AgentResult:
        ...
```

## 15.3 GeneralAgent

MVP 默认 Agent：

```text
GeneralAgent
→ uses general skill
→ supports model loop
→ supports tool calling
→ writes summary memory
```

## 15.4 Multi-Agent MVP

MVP 支持 A2A 协议，但多智能体执行可先做薄实现：

```text
1. AgentCard 暴露。
2. A2A task 接收。
3. 将 A2A task 转换为内部 AgentRequest。
4. 使用 GeneralAgent 执行。
5. 返回 A2A task result。
```

## 15.5 A2A 目录

```text
multi_agent/
├── protocols/
│   ├── a2a.py
│   └── internal.py
├── orchestrator.py
├── subagent.py
├── delegation.py
└── result_collection.py
```

## 15.6 AgentCard

```python
class AgentCard(BaseModel):
    name: str
    version: str
    description: str
    capabilities: list[str]
    input_modes: list[str] = ["text"]
    output_modes: list[str] = ["text"]
    endpoints: dict[str, str]
```

Example:

```json
{
  "name": "general-agent",
  "version": "0.1.0",
  "description": "General purpose agent",
  "capabilities": ["tool_use", "mcp", "summary_memory"],
  "endpoints": {
    "tasks": "/v1/a2a/tasks"
  }
}
```

---

## 16. Tool System 设计

## 16.1 目录

```text
tools/
├── base.py
├── definition.py
├── registry.py
├── router.py
├── executor.py
├── observation.py
├── governance/
│   ├── permissions.py
│   ├── risk.py
│   └── schema_validator.py
├── execution/
│   ├── retry.py
│   ├── idempotency.py
│   └── timeout.py
├── builtins/
│   ├── echo.py
│   ├── datetime.py
│   ├── calculator.py
│   ├── filesystem.py
│   ├── http.py
│   └── python_exec.py
└── mcp/
    ├── client.py
    ├── server.py
    ├── tool_adapter.py
    └── schemas.py
```

## 16.2 Tool 接口

```python
class Tool(Protocol):
    definition: ToolDefinition

    async def invoke(self, invocation: ToolInvocation) -> ToolResult:
        ...
```

## 16.3 ToolRouter 流程

```text
Model ToolCall
→ lookup ToolDefinition
→ validate allowed by Skill
→ validate JSON schema
→ run before_tool_call hooks
→ choose executor
→ execute
→ validate output schema
→ run after_tool_call hooks
→ append observation
```

## 16.4 MVP Builtin Tools

| Tool | Risk | Sandbox | 说明 |
|---|---|---|---|
| builtin.echo | low | no | 回显 |
| builtin.datetime | low | no | 当前时间 |
| builtin.calculator | low | no | 基础计算 |
| builtin.read_file | medium | no | 通过 VFS 读取文件 |
| builtin.write_file | medium | no | 通过 VFS 写文件 |
| builtin.python_exec | high | yes | subprocess 执行 Python，默认禁用或需显式开启 |
| mcp.* | medium | depends | MCP tool adapter |
| a2a.* | medium | no | A2A remote agent call |

---

## 17. MCP 设计

## 17.1 MCP Client

用于调用外部 MCP Server 暴露的 tools/resources/prompts。

```text
tools/mcp/client.py
```

```python
class MCPClient:
    async def list_tools(self) -> list[ToolDefinition]:
        ...

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        ...

    async def list_resources(self) -> list[MCPResource]:
        ...
```

## 17.2 MCP Server

平台自身可以暴露 MCP 工具。

MVP 暴露：

```text
list_tools
call_tool
list_resources
read_resource
list_prompts
get_prompt
```

## 17.3 MCP Tool Adapter

```python
class MCPToolAdapter:
    async def sync_tools(self, mcp_server: MCPServerConfig) -> list[ToolDefinition]:
        ...

    async def invoke(self, invocation: ToolInvocation) -> ToolResult:
        ...
```

## 17.4 MCP 配置

```yaml
mcp_servers:
  local_tools:
    command: "python"
    args: ["-m", "some_mcp_server"]
    enabled: true
```

---

## 18. Context Manager 设计

## 18.1 目录

```text
context/
├── assembler.py
├── budget.py
├── compressor.py
├── summarizer.py
├── window.py
├── injection.py
├── tool_observation.py
└── schemas.py
```

## 18.2 ContextBundle

```python
class ContextBundle(BaseModel):
    run: AgentRun
    session_messages: list[Message] = []
    memory_summary: str | None = None
    tool_observations: list[ToolResult] = []
    workspace_files: list[str] = []
    constraints: dict[str, Any] = {}
    token_budget: int | None = None
```

## 18.3 Assemble 流程

```text
Load agent run
→ Load session history
→ Load summary memory
→ Load pending observations
→ Load workspace listing
→ Apply token budget
→ Return ContextBundle
```

---

## 19. Memory 设计：Summary Memory MVP

## 19.1 目录

```text
memory/
├── base.py
├── manager.py
├── schemas.py
├── policy.py
├── extractor.py
├── consolidation.py
├── stores/
│   └── summary.py
└── backends/
    ├── filesystem.py
    └── postgres.py
```

## 19.2 MemoryManager

```python
class MemoryManager:
    async def get_summary(self, session_id: str | None) -> str | None:
        ...

    async def maybe_update_summary(self, run: AgentRun, response: ModelResponse) -> MemoryItem | None:
        ...
```

## 19.3 Summary 更新策略

MVP 策略：

```text
1. 每个 completed agent run 后判断是否需要更新 summary。
2. 如果 session_id 不存在，则使用 agent_run_id 级 summary。
3. 使用 summarizer prompt 生成新 summary。
4. before_memory_write hook 检查。
5. 保存 MemoryItem(type="summary")。
```

## 19.4 Summary Prompt

```text
请根据以下历史摘要、用户目标、最终回答，生成简洁的会话摘要。
摘要应包括：
1. 用户目标。
2. 已完成事项。
3. 关键结论。
4. 后续可用上下文。
不要记录敏感信息。
```

---

## 20. VFS 设计

## 20.1 目录

```text
vfs/
├── base.py
├── manager.py
├── path.py
├── permissions.py
├── snapshot.py
├── diff.py
├── mounts/
│   ├── workspace.py
│   ├── artifacts.py
│   └── memories.py
└── backends/
    ├── local.py
    └── memory.py
```

## 20.2 VFS Root

MVP 本地路径：

```text
.data/
├── workspace/
│   └── {agent_run_id}/
├── artifacts/
│   └── {agent_run_id}/
└── memories/
```

## 20.3 VFS 接口

```python
class VFS:
    async def read_text(self, path: str) -> str:
        ...

    async def write_text(self, path: str, content: str) -> FileRef:
        ...

    async def list(self, path: str) -> list[FileRef]:
        ...

    async def delete(self, path: str) -> None:
        ...
```

路径约束：

```text
/workspace/{agent_run_id}/...
/artifacts/{agent_run_id}/...
/memories/...
```

禁止 `..` 路径穿越。

---

## 21. Sandbox 设计：Subprocess Runner MVP

## 21.1 目录

```text
sandbox/
├── base.py
├── manager.py
├── policy.py
├── resource_limits.py
├── filesystem_policy.py
├── network_policy.py
└── runners/
    ├── subprocess.py
    └── python.py
```

## 21.2 MVP 限制

```text
仅开发环境使用。
默认禁用 shell。
python_exec 必须显式开启。
限制 cwd 为 /workspace/{agent_run_id}。
限制 timeout。
捕获 stdout/stderr。
不保证强安全隔离。
```

## 21.3 SubprocessRunner

```python
class SubprocessSandboxRunner:
    async def run(
        self,
        command: list[str],
        cwd: str,
        timeout_seconds: int,
        env: dict[str, str] | None = None,
    ) -> SandboxResult:
        ...
```

---

## 22. Policy / Governance 设计

## 22.1 Policy 目录

```text
policy/
├── engine.py
├── rules.py
├── context.py
├── decisions.py
├── registry.py
└── builtin/
    ├── tool_policy.yaml
    ├── memory_policy.yaml
    └── prompt_policy.yaml
```

## 22.2 PolicyDecision

```python
class PolicyDecision(BaseModel):
    allowed: bool
    reason: str | None = None
    requires_approval: bool = False
    modified_payload: dict[str, Any] | None = None
```

## 22.3 Tool Policy MVP

```yaml
tools:
  builtin.echo:
    allowed: true
  builtin.datetime:
    allowed: true
  builtin.calculator:
    allowed: true
  builtin.read_file:
    allowed: true
    scopes:
      - workspace:read
  builtin.write_file:
    allowed: true
    scopes:
      - workspace:write
  builtin.python_exec:
    allowed: false
    reason: "Disabled by default in MVP"
  builtin.shell:
    allowed: false
```

## 22.4 Governance 目录

```text
governance/
├── risk_classifier.py
├── guardrails.py
├── approvals.py
├── human_review.py
├── secrets.py
├── audit.py
└── schemas.py
```

MVP：

```text
audit log 必须实现。
approval 仅 stub。
secrets 仅从 env 读取，不落日志。
guardrails 实现 prompt/tool 基础检查。
```

---

## 23. Deployment 设计

## 23.1 目标

第一版纳入 Prompt、Skill、Policy 版本发布。

## 23.2 目录

```text
deployment/
├── manifest.py
├── release.py
├── environment.py
├── version.py
├── lockfile.py
├── resolver.py
└── schemas.py
```

## 23.3 Deployment Lockfile

```yaml
version: 0.1.0
environment: dev

skills:
  general: 0.1.0

prompts:
  general_agent.system: 0.1.0
  general_agent.entry: 0.1.0
  summarizer.session_summary: 0.1.0

policies:
  tool_policy: 0.1.0
  memory_policy: 0.1.0
```

## 23.4 Resolver

```python
class DeploymentResolver:
    def resolve_skill_version(self, name: str) -> str:
        ...

    def resolve_prompt_version(self, name: str) -> str:
        ...

    def resolve_policy_version(self, name: str) -> str:
        ...
```

---

## 24. Storage 设计

## 24.1 MVP 存储选择

开发阶段默认 SQLite，生产可切 PostgreSQL。

```yaml
storage:
  database_url: "sqlite+aiosqlite:///./.data/agent_platform.db"
  object_root: "./.data"
```

## 24.2 表设计

### agent_runs

| 字段 | 类型 | 说明 |
|---|---|---|
| agent_run_id | string pk | agent run id |
| session_id | string nullable | session id |
| input_message_id | string nullable | initiating user message |
| mode | string | chat/plan/build/review |
| requested_pattern | string nullable | requested pattern |
| active_pattern | string nullable | selected/current pattern |
| context_message_sequence | int nullable | session history watermark |
| status | string | agent run status |
| trace_id | string | run trace |
| finish_reason | string nullable | completion reason |
| error_type | string nullable | terminal failure category |
| max_steps | int | max step |
| timeout_seconds | int | timeout |
| metadata | json | metadata |
| created_at | datetime | created time |
| updated_at | datetime | updated time |

### agent_run_steps

| 字段 | 类型 | 说明 |
|---|---|---|
| step_id | string pk | step id |
| agent_run_id | string index | agent run id |
| index | int | step index |
| kind | string | pattern_selection/model_invocation/tool_execution/finalization/... |
| pattern | string nullable | pattern owning the step |
| invocation_id | string nullable | associated model invocation |
| status | string | pending/running/completed/failed |
| input | json | input |
| output | json | output |
| error | text nullable | error |
| created_at | datetime | created |
| updated_at | datetime | updated |

### runtime_events

| 字段 | 类型 | 说明 |
|---|---|---|
| event_id | string pk | event id |
| event_type | string index | event type |
| event_version | string | schema version |
| agent_run_id | string index nullable | agent run id |
| session_id | string nullable | session id |
| trace_id | string index | trace id |
| span_id | string | span id |
| parent_span_id | string nullable | parent span |
| actor_type | string | actor type |
| actor_id | string nullable | actor id |
| payload | json | payload |
| created_at | datetime | created |

### sessions

| 字段 | 类型 | 说明 |
|---|---|---|
| session_id | string pk | session id |
| title | string nullable | title |
| metadata | json | metadata |
| created_at | datetime | created |
| updated_at | datetime | updated |

### session_messages

| 字段 | 类型 | 说明 |
|---|---|---|
| message_id | string pk | message id |
| session_id | string index | session id |
| sequence | int | monotonically increasing session order |
| agent_run_id | string nullable | producing/consuming run |
| role | string | role |
| content | text | content |
| metadata | json | metadata |
| created_at | datetime | created |

### memory_items

| 字段 | 类型 | 说明 |
|---|---|---|
| memory_id | string pk | memory id |
| session_id | string nullable | session id |
| source_agent_run_id | string nullable | producing run |
| type | string | summary |
| content | text | summary content |
| metadata | json | metadata |
| created_at | datetime | created |
| updated_at | datetime | updated |

### artifacts

| 字段 | 类型 | 说明 |
|---|---|---|
| artifact_id | string pk | artifact id |
| agent_run_id | string index | producing run |
| path | string | vfs path |
| type | string | report/file/json/etc |
| metadata | json | metadata |
| created_at | datetime | created |

### deployments

| 字段 | 类型 | 说明 |
|---|---|---|
| deployment_id | string pk | deployment id |
| environment | string | dev/staging/prod |
| version | string | version |
| lockfile | json | resolved versions |
| active | bool | active |
| created_at | datetime | created |

---

## 25. Observability 设计

## 25.1 目录

```text
observability/
├── tracing.py
├── metrics.py
├── logging.py
├── spans.py
├── cost.py
├── token_usage.py
└── alerts.py
```

## 25.2 MVP 要求

每个 agent run 记录：

```text
trace_id
agent_run_id
model calls
model latency
input/output tokens
estimated cost
tool calls
tool latency
errors
```

## 25.3 Event 与 Trace 关系

```text
RuntimeEvent.trace_id = AgentRun.trace_id
RuntimeEvent.span_id = 每个 step/tool/model call 唯一 span
```

---

## 26. Workers 设计

## 26.1 MVP 方案

第一版可以使用 asyncio background task，不引入 Celery。

```text
workers/
├── app.py
├── runtime_worker.py
├── tool_worker.py
├── memory_worker.py
└── queues.py
```

## 26.2 Worker 类型

| Worker | MVP 是否实现 | 说明 |
|---|---|---|
| RuntimeWorker | 是 | 执行 agent run |
| ToolWorker | 可选 | 初期同步执行，后期异步化 |
| MemoryWorker | 可选 | summary 可同步更新 |
| SandboxWorker | 否 | Phase 3 |
| EvalWorker | 否 | Phase 4 |

---

## 27. Config 设计

## 27.1 `.env.example`

```env
AGENT_PLATFORM_ENV=dev
AGENT_PLATFORM_API_KEY=dev-key
DATABASE_URL=sqlite+aiosqlite:///./.data/agent_platform.db
OBJECT_ROOT=./.data
OPENAI_API_KEY=
OPENAI_DEFAULT_MODEL=gpt-4.1-mini
DEFAULT_MODEL_PROVIDER=openai
ENABLE_MOCK_MODEL=true
ENABLE_SUBPROCESS_SANDBOX=false
```

## 27.2 `configs/app.yaml`

```yaml
app:
  name: agent-platform
  environment: dev
  single_tenant: true

runtime:
  max_steps: 30
  timeout_seconds: 600
  default_skill: general

models:
  default_provider: openai
  fallback_provider: mock

memory:
  enabled: true
  type: summary

sandbox:
  subprocess_enabled: false
  timeout_seconds: 30

mcp:
  enabled: true
  servers: []

a2a:
  enabled: true
```

## 27.3 `configs/deployment.lock.yaml`

```yaml
version: 0.1.0
environment: dev
skills:
  general: 0.1.0
prompts:
  general_agent.system: 0.1.0
  general_agent.entry: 0.1.0
  summarizer.session_summary: 0.1.0
policies:
  tool_policy: 0.1.0
  memory_policy: 0.1.0
```

---

## 28. Error Handling 设计

## 28.1 错误类型

```python
class AgentPlatformError(Exception): ...
class PolicyDeniedError(AgentPlatformError): ...
class HookBlockedError(AgentPlatformError): ...
class ToolNotFoundError(AgentPlatformError): ...
class ToolValidationError(AgentPlatformError): ...
class ModelInvocationError(AgentPlatformError): ...
class PromptRenderError(AgentPlatformError): ...
class SkillResolveError(AgentPlatformError): ...
class RuntimeTimeoutError(AgentPlatformError): ...
```

## 28.2 错误事件

所有未捕获异常写入：

```text
AgentRunFailed
ModelCallFailed
ToolCallFailed
PromptRenderFailed
HookBlocked
PolicyDenied
```

## 28.3 错误响应格式

```json
{
  "error": {
    "code": "TOOL_VALIDATION_ERROR",
    "message": "Invalid tool arguments",
    "details": {}
  }
}
```

---

## 29. Security 低层设计

## 29.1 MVP 安全原则

```text
1. 单租户，但所有 schema 保留 tenant_id 字段。
2. API 需要 dev API key。
3. Tool 默认最小权限。
4. subprocess sandbox 默认关闭。
5. Secret 不写入 event payload。
6. VFS 禁止路径穿越。
7. 高风险工具默认 block。
8. MCP tool 同样纳入 Tool Policy。
9. A2A 外部调用需要配置 allowlist。
```

## 29.2 Secret Redaction

```python
SENSITIVE_KEYS = {"api_key", "token", "secret", "password", "authorization"}
```

所有日志与事件 payload 写入前经过 redaction。

---

## 30. MVP 端到端流程示例

### 30.1 API 调用

```bash
curl -X POST http://localhost:8000/v1/agent-runs \
  -H "Authorization: Bearer dev-key" \
  -H "Content-Type: application/json" \
  -d '{"goal":"帮我制定一个 Python Agent 项目的启动计划"}'
```

### 30.2 内部流程

```text
POST /v1/agent-runs
→ AccessContext(default/local-user)
→ AgentRunCreated
→ RuntimeWorker picks agent run
→ SkillResolver: general@0.1.0
→ ContextAssembler: no history, no summary
→ PromptEngine render general_agent.entry@0.1.0
→ OpenAIModelAdapter.invoke
→ response without tool call
→ SummaryMemory updated
→ AgentRunCompleted
→ return response
```

### 30.3 工具调用流程

如果模型请求：

```json
{
  "name": "builtin.calculator",
  "arguments": {"expression":"1+1"}
}
```

流程：

```text
ToolRouter lookup builtin.calculator
→ Skill allowed check
→ JSON schema validation
→ before_tool_call hook
→ invoke CalculatorTool
→ after_tool_call hook
→ ToolExecuted event
→ append observation
→ continue model loop
```

---

## 31. 测试设计

## 31.1 单元测试

```text
tests/unit/
├── test_runtime_state_machine.py
├── test_prompt_renderer.py
├── test_skill_resolver.py
├── test_hook_manager.py
├── test_tool_router.py
├── test_tool_schema_validation.py
├── test_summary_memory.py
├── test_vfs_path_safety.py
├── test_model_mock_adapter.py
└── test_deployment_resolver.py
```

## 31.2 集成测试

```text
tests/integration/
├── test_agent_run_api.py
├── test_agent_loop_no_tool.py
├── test_agent_loop_with_tool.py
├── test_mcp_tool_call.py
├── test_a2a_task_create.py
├── test_summary_memory_update.py
└── test_replay_events.py
```

## 31.3 MVP 验收测试

| 测试 | 预期 |
|---|---|
| 创建 agent run | 返回 agent_run_id |
| mock model 完成执行 | agent run completed |
| OpenAI model 完成执行 | agent run completed |
| calculator tool call | 结果写入 observation |
| high risk tool | 被 hook/policy 阻断 |
| summary memory | agent run 完成后写入 summary |
| events replay | 能查询完整事件列表 |
| prompt version lock | 使用 deployment lock 中版本 |
| mcp list tools | 返回 MCP tools |
| a2a agent card | 返回 AgentCard |

---

## 32. 推荐开发顺序

### Sprint 1：基础骨架

1. pyproject / settings / logging。
2. contracts 基础 schema。
3. storage + migrations。
4. FastAPI app + health。
5. CLI skeleton。

### Sprint 2：Runtime + Events

1. AgentRun repository（放在 `src/storage/database/repositories`）。
2. Event store（repository/model 放在 `src/storage/database`）。
3. Runtime state machine。
4. Runtime loop with mock model。
5. AgentRun API。

### Sprint 3：Prompt + Model

1. Prompt registry/loader/renderer。
2. Deployment lock resolver。
3. Mock adapter。
4. OpenAI adapter。
5. Prompt render API。

### Sprint 4：Skill + Hooks

1. Skill manifest loader。
2. General skill。
3. Hook manager。
4. Builtin tracing/audit/tool risk hooks。
5. Skill resolver integration。

### Sprint 5：Tools + VFS + Memory

1. Tool registry/router/executor。
2. Builtin tools。
3. Local VFS。
4. Summary memory。
5. Tool loop integration。

### Sprint 6：MCP + A2A + Hardening

1. MCP client/server minimal。
2. A2A agent card/task endpoint。
3. Error handling。
4. Observability polish。
5. End-to-end examples。

---

## 33. MVP Definition of Done

MVP 完成需满足：

```text
1. API 可创建并执行通用 AgentRun。
2. CLI 可运行通用 AgentRun。
3. 支持 OpenAI 与 Mock Model。
4. 支持 Prompt 模板渲染与版本锁定。
5. 支持 General Skill 加载。
6. 支持 Hook 生命周期拦截。
7. 支持 Tool Registry、Tool Call、Tool Policy。
8. 支持 MCP server/client 基础能力。
9. 支持 A2A agent card 与 task endpoint。
10. 支持 Summary Memory。
11. 支持 Local VFS。
12. 支持 Event Store 与 AgentRun replay 查询。
13. 支持基础 Observability：trace、token、cost、latency。
14. 高风险工具默认被阻断。
15. 单元测试覆盖 Runtime、Prompt、Skill、Hook、Tool、Memory、VFS。
```

---

## 34. 后续 Phase 扩展点

MVP 后续可扩展：

```text
1. Docker sandbox。
2. Semantic / Entity / Episodic memory。
3. Knowledge ingestion + RAG。
4. Full multi-agent orchestration。
5. Reflection / parallelization 默认执行路径。
6. Evaluation / regression。
7. Web control plane。
8. Multi-tenant isolation。
9. Plugin marketplace。
10. Policy language。
11. Deployment rollout / rollback。
12. Distributed worker queue。
```

---

## 35. 结论

本 LLD 将 PRD 收敛为一个可落地的 MVP：

```text
通用 Agent
API + CLI
OpenAI + Mock
Summary Memory
MCP + A2A
Prompt/Skill/Policy Versioned Deployment
Subprocess Sandbox for Dev
Single Tenant
No Eval Blocking
```

核心实现原则：

```text
contracts 统一协议
runtime 驱动执行
events 记录事实
prompts 编译语言输入
skills 组合能力
hooks 注入治理
tools 受控行动
memory 保存摘要状态
vfs 限制文件边界
deployment 锁定版本
```

该设计可在不依赖外部 Agent 框架的前提下，形成自研 Agent Platform 的稳定技术底座。
