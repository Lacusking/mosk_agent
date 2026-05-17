# 自研 Agent Platform 二期低层设计文档（Phase 2 LLD）

版本：v0.1  
状态：Draft  
目标实现语言：Python 3.12+  
依赖基线：MVP LLD v0.1  
阶段定位：MVP 后的剩余核心能力开发与平台化增强

---

## 1. 文档目的

本文档定义 Agent Platform 二期开发的低层设计。

一期 MVP 已覆盖：

```text
通用 Agent
API + CLI
OpenAI + Mock
Summary Memory
Prompt / Skill / Hook / Tool 基础能力
MCP / A2A 基础能力
Local VFS
开发环境 subprocess sandbox
单租户
Event Store / Replay 基础能力
Deployment lockfile 基础能力
```

二期目标是将 MVP 中的 stub、基础版、保留目录和非阻塞能力补齐，使平台从“可运行的通用 Agent Runtime”升级为“可扩展、可治理、可评估、可部署的 Agent Platform”。

---

## 2. 二期总体目标

### 2.1 二期一句话目标

完成 MVP 剩余功能开发，重点补齐：

```text
Workflow Engine
Full Multi-Agent
Connectors
Knowledge / RAG
Advanced Memory
Docker Sandbox
Policy Language
Control Plane
Evaluation / Replay / Regression
Notifications
Advanced Deployment
Plugins
```

### 2.2 二期不是重写 MVP

二期不应重写 Runtime 主链路，而是在 MVP 架构上扩展能力。

保持不变的核心边界：

```text
runtime/      仍然负责执行生命周期
contracts/    仍然是跨模块协议来源
events/       仍然是事实记录与回放基础
prompts/      仍然负责编译 Prompt
skills/       仍然负责能力组合
tools/        仍然负责原子行动
hooks/        仍然负责生命周期扩展
```

二期重点是将以下模块从“基础版 / stub”升级为“可生产使用”：

```text
workflow/
multi_agent/
connectors/
knowledge/
rag/
memory/
sandbox/
policy/
governance/
evaluation/
experiments/
notifications/
control_plane/
deployment/
plugins/
```

---

## 3. 二期范围定义

## 3.1 二期必须完成的能力

| 模块 | 二期目标 |
|---|---|
| workflow/ | 从基础 DAG runner 升级为可版本化、可重试、可补偿的工作流引擎 |
| multi_agent/ | 支持 Supervisor、Subagent、Role-based、Hierarchical、结果聚合与上下文隔离 |
| connectors/ | 支持外部系统连接器框架，首批实现 GitHub、HTTP、PostgreSQL、Slack/Webhook |
| knowledge/ | 支持文档摄取、解析、切分、元数据、来源追踪、权限 |
| rag/ | 支持 embedding、retriever、reranker stub、citation、grounding 注入 |
| memory/ | 从 summary memory 扩展到 semantic/entity/episodic memory |
| sandbox/ | 从 subprocess dev runner 扩展到 Docker runner，支持资源限制、网络策略、VFS mount |
| policy/ | 从简单规则升级为策略注册、策略上下文、策略决策与规则 DSL |
| governance/ | 增强人工审批、审计、secret scope、guardrails、风险分级 |
| evaluation/ | 支持轨迹评估、工具调用评估、最终答案评估、回归数据集与 replay debug |
| notifications/ | 支持 Webhook、Slack、Email stub、审批通知、任务完成通知 |
| control_plane/ | 支持 Prompt、Skill、Tool、Policy、Agent、Deployment 管理 API |
| deployment/ | 支持 release、environment、rollout、rollback、lockfile 管理 |
| plugins/ | 支持本地插件加载，插件可提供 tool、skill、hook、connector |

## 3.2 二期可选能力

| 能力 | 处理方式 |
|---|---|
| Firecracker sandbox | 保留接口，二期不强制实现 |
| 完整 marketplace | 保留插件源接口，二期只做本地插件 |
| 多租户生产隔离 | 继续保留 tenant_id 字段，二期可做轻量 project isolation，不做完整多租户计费 |
| 复杂 ABAC | 二期实现基础 ABAC 条件，复杂策略推迟 |
| 高级实验平台 | 二期实现 prompt/model/routing experiment 基础能力 |
| Web UI | 二期仍不作为必选，Control Plane 先以 API/CLI 形式提供 |

---

## 4. 二期架构变化

### 4.1 MVP 架构

```text
API / CLI
→ Runtime
→ Skill / Prompt / Hook
→ Model / Tool
→ Summary Memory / VFS
→ Events / Storage
```

### 4.2 二期目标架构

```text
API / CLI / Control Plane
→ Runtime Kernel
→ Skill Engine / Prompt Engine / Hook Engine / Workflow Engine
→ Agent / Multi-Agent Orchestrator
→ Tool Router / Connector / MCP / A2A / Sandbox
→ Context / Memory / Knowledge / RAG
→ VFS / Artifacts / Storage
→ Policy / Governance / Observability / Evaluation / Deployment
```

### 4.3 二期主执行链路

```text
User Request
→ Access Normalize
→ Runtime Create Task
→ Skill Resolve
→ Workflow Resolve or Plan Generate
→ Multi-Agent Orchestration
→ Context Assemble
→ RAG Retrieve
→ Prompt Render
→ Model Call
→ Tool / Connector / MCP / A2A / Sandbox Execution
→ Observation Append
→ Reflection / Verification
→ Memory Write Candidate
→ Policy Decision
→ Artifact Persist
→ Evaluation Run
→ Notification Dispatch
→ Final Response
```

---

## 5. 二期模块开发总览

```text
src/agent_platform/
├── workflow/            # 二期重点：工作流引擎完整化
├── multi_agent/         # 二期重点：多智能体完整化
├── connectors/          # 二期重点：外部系统连接器
├── knowledge/           # 二期重点：知识资产管理
├── rag/                 # 二期重点：检索增强
├── memory/              # 二期重点：高级记忆
├── sandbox/             # 二期重点：Docker sandbox
├── policy/              # 二期重点：策略引擎升级
├── governance/          # 二期重点：审批、审计、安全治理
├── evaluation/          # 二期重点：评估与回归
├── experiments/         # 二期增强：实验与灰度
├── notifications/       # 二期增强：通知与回调
├── control_plane/       # 二期重点：控制面 API
├── deployment/          # 二期重点：发布与回滚
├── plugins/             # 二期增强：本地插件体系
└── artifacts/           # 二期增强：产物生命周期
```

---

# 6. Workflow Engine 二期设计

## 6.1 目标

MVP 的 workflow 是基础版。二期需要支持：

```text
Workflow Definition
Workflow Version
DAG Execution
Conditional Transition
Retry Policy
Compensation
Human Approval Step
Tool Step
Agent Step
Subworkflow
State Persistence
Replay Integration
```

## 6.2 目录结构

```text
workflow/
├── __init__.py
├── definition.py
├── engine.py
├── runner.py
├── state.py
├── step.py
├── transition.py
├── conditions.py
├── retry.py
├── compensation.py
├── registry.py
├── loader.py
├── versioning.py
├── schemas.py
└── builtin/
    ├── general_task.yaml
    ├── research_workflow.yaml
    ├── code_review_workflow.yaml
    └── data_analysis_workflow.yaml
```

## 6.3 WorkflowDefinition

```python
from typing import Any, Literal
from pydantic import BaseModel, Field

WorkflowStepType = Literal[
    "model", "tool", "agent", "subagent", "human", "condition", "subworkflow", "system"
]

class WorkflowRetryPolicy(BaseModel):
    max_attempts: int = 1
    backoff_seconds: float = 0.0
    retry_on: list[str] = Field(default_factory=list)

class WorkflowStepDefinition(BaseModel):
    id: str
    name: str
    type: WorkflowStepType
    input: dict[str, Any] = Field(default_factory=dict)
    depends_on: list[str] = Field(default_factory=list)
    condition: str | None = None
    retry: WorkflowRetryPolicy = Field(default_factory=WorkflowRetryPolicy)
    compensation_step: str | None = None
    timeout_seconds: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

class WorkflowDefinition(BaseModel):
    name: str
    version: str
    description: str | None = None
    steps: list[WorkflowStepDefinition]
    inputs: dict[str, Any] = Field(default_factory=dict)
    outputs: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
```

## 6.4 WorkflowState

```python
class WorkflowRunStatus(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    WAITING_HUMAN = "waiting_human"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class WorkflowStepRun(BaseModel):
    step_id: str
    status: str
    attempts: int = 0
    input: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None

class WorkflowRunState(BaseModel):
    run_id: str
    workflow_name: str
    workflow_version: str
    task_id: str
    status: WorkflowRunStatus
    steps: dict[str, WorkflowStepRun]
    variables: dict[str, Any] = Field(default_factory=dict)
```

## 6.5 WorkflowRunner 执行逻辑

```python
async def run_workflow(run_state: WorkflowRunState) -> WorkflowRunState:
    while not is_terminal(run_state):
        ready_steps = get_ready_steps(run_state)

        if not ready_steps:
            break

        for step in ready_steps:
            await events.append("WorkflowStepStarted", payload={"step_id": step.id})
            try:
                result = await execute_step(step, run_state)
                mark_completed(run_state, step.id, result)
                await events.append("WorkflowStepCompleted", payload={"step_id": step.id})
            except Exception as exc:
                if should_retry(step, exc):
                    schedule_retry(run_state, step.id)
                else:
                    await run_compensation_if_needed(step, run_state)
                    mark_failed(run_state, step.id, exc)
                    await events.append("WorkflowStepFailed", payload={"step_id": step.id, "error": str(exc)})
                    if is_required_step(step):
                        run_state.status = WorkflowRunStatus.FAILED
                        return run_state

    run_state.status = WorkflowRunStatus.COMPLETED
    return run_state
```

## 6.6 Workflow 与 Runtime 的集成

```text
Runtime StepRunner
  if step.type == workflow:
      WorkflowEngine.start_or_resume(workflow_name, task_id)
```

事件：

```text
WorkflowRunCreated
WorkflowStepStarted
WorkflowStepCompleted
WorkflowStepFailed
WorkflowRunCompleted
WorkflowRunFailed
```

---

# 7. Multi-Agent 二期设计

## 7.1 目标

MVP 只支持 A2A 基础 endpoint。二期补齐真正多智能体能力。

能力：

```text
Supervisor Agent
Role Agent
Ephemeral Subagent
Task Delegation
Context Isolation
Result Collection
Hierarchical Orchestration
Collaborative Orchestration
Debate Pattern 基础版
Internal A2A Bus
External A2A Endpoint
```

## 7.2 目录结构

```text
multi_agent/
├── __init__.py
├── orchestrator.py
├── supervisor.py
├── delegation.py
├── subagent.py
├── lifecycle.py
├── isolation.py
├── result_collection.py
├── coordination.py
├── communication.py
├── registry.py
├── schemas.py
├── protocols/
│   ├── a2a.py
│   ├── internal.py
│   └── mcp.py
└── patterns/
    ├── hierarchical.py
    ├── collaborative.py
    ├── role_based.py
    └── debate.py
```

## 7.3 AgentCard 扩展

```python
class AgentCapability(BaseModel):
    name: str
    description: str | None = None
    input_schema: dict[str, Any] | None = None
    output_schema: dict[str, Any] | None = None

class AgentCard(BaseModel):
    agent_id: str
    name: str
    version: str
    description: str
    role: str | None = None
    capabilities: list[AgentCapability]
    allowed_tools: list[str] = Field(default_factory=list)
    memory_scope: str = "task"
    risk_level: str = "medium"
    endpoints: dict[str, str] = Field(default_factory=dict)
```

## 7.4 SubAgentContext

```python
class SubAgentContext(BaseModel):
    parent_task_id: str
    subtask_id: str
    agent_id: str
    goal: str
    allowed_tools: list[str]
    allowed_vfs_paths: list[str]
    memory_read_scope: list[str]
    memory_write_mode: Literal["none", "summary_only", "propose"] = "none"
    max_steps: int = 10
    timeout_seconds: int = 300
    metadata: dict[str, Any] = Field(default_factory=dict)
```

## 7.5 Delegation Flow

```text
Supervisor receives root task
→ Planning Engine creates task decomposition
→ MultiAgentOrchestrator selects role agents
→ Create SubAgentContext per subtask
→ Run subagents isolated
→ Collect structured results
→ Critic Agent optionally reviews
→ Supervisor merges final result
```

## 7.6 ResultCollection

```python
class SubAgentResult(BaseModel):
    subtask_id: str
    agent_id: str
    status: str
    result: dict[str, Any]
    artifacts: list[str] = Field(default_factory=list)
    events: list[str] = Field(default_factory=list)
    error: str | None = None

class AggregatedAgentResult(BaseModel):
    parent_task_id: str
    results: list[SubAgentResult]
    merged_content: str | None = None
    conflicts: list[dict[str, Any]] = Field(default_factory=list)
```

## 7.7 多智能体模式

| 模式 | 二期实现级别 |
|---|---|
| Hierarchical | 完整实现：Supervisor → Role Agents |
| Role-based | 完整实现：Researcher/Executor/Critic/Writer |
| Collaborative | 基础实现：共享 task-level observations |
| Debate | 基础实现：多候选答案 + critic 选择 |
| Market-based | 不实现，保留接口 |

---

# 8. Connectors 二期设计

## 8.1 目标

区分 tools 与 connectors：

```text
connector = 外部系统 API 封装、认证、限流、连接管理
tool = 暴露给 Agent 调用的原子动作
```

## 8.2 目录结构

```text
connectors/
├── __init__.py
├── base.py
├── registry.py
├── auth.py
├── credentials.py
├── rate_limit.py
├── schemas.py
├── http/
│   ├── client.py
│   └── connector.py
├── github/
│   ├── client.py
│   ├── connector.py
│   └── schemas.py
├── slack/
│   ├── client.py
│   └── connector.py
├── postgres/
│   ├── client.py
│   └── connector.py
└── webhook/
    ├── client.py
    └── connector.py
```

## 8.3 Connector 接口

```python
class Connector(Protocol):
    name: str

    async def connect(self) -> None:
        ...

    async def close(self) -> None:
        ...

    async def health_check(self) -> bool:
        ...
```

## 8.4 Credential Binding

```python
class ConnectorCredential(BaseModel):
    connector_name: str
    credential_type: Literal["api_key", "oauth", "basic", "none"]
    secret_ref: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
```

## 8.5 首批 Connector

| Connector | 用途 | 暴露 Tool |
|---|---|---|
| http | 通用 HTTP 请求 | http.get, http.post |
| github | 仓库、Issue、PR | github.get_repo, github.create_issue, github.comment_pr |
| slack | 通知、消息 | slack.post_message |
| postgres | SQL 查询 | postgres.query |
| webhook | 外部回调 | webhook.send |

---

# 9. Knowledge / RAG 二期设计

## 9.1 Knowledge 目标

Knowledge 管理知识资产，不直接等于 RAG。

能力：

```text
Document Ingestion
Parser
Chunking
Metadata
Provenance
Permission
Freshness
Indexing
```

## 9.2 Knowledge 目录

```text
knowledge/
├── __init__.py
├── corpus.py
├── document.py
├── source.py
├── ingestion.py
├── parser.py
├── chunking.py
├── indexing.py
├── metadata.py
├── permissions.py
├── freshness.py
├── citation.py
├── provenance.py
├── schemas.py
└── parsers/
    ├── markdown.py
    ├── text.py
    ├── html.py
    ├── pdf.py
    └── code.py
```

## 9.3 Knowledge Schema

```python
class KnowledgeDocument(BaseModel):
    document_id: str
    corpus_id: str
    title: str | None = None
    source_uri: str | None = None
    content_type: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

class KnowledgeChunk(BaseModel):
    chunk_id: str
    document_id: str
    corpus_id: str
    text: str
    index: int
    metadata: dict[str, Any] = Field(default_factory=dict)
```

## 9.4 RAG 目录

```text
rag/
├── __init__.py
├── retriever.py
├── chunker.py
├── embeddings.py
├── reranker.py
├── citation.py
├── grounding.py
├── ingestion.py
├── indexes.py
└── schemas.py
```

## 9.5 Embedding 接口

```python
class EmbeddingModel(Protocol):
    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        ...
```

MVP+二期默认：

```text
OpenAI embeddings
Mock embeddings for tests
```

## 9.6 Retriever 接口

```python
class RetrievalQuery(BaseModel):
    query: str
    corpus_ids: list[str] = Field(default_factory=list)
    limit: int = 5
    filters: dict[str, Any] = Field(default_factory=dict)

class RetrievalResult(BaseModel):
    chunk_id: str
    document_id: str
    text: str
    score: float
    citation: dict[str, Any] = Field(default_factory=dict)

class Retriever(Protocol):
    async def retrieve(self, query: RetrievalQuery) -> list[RetrievalResult]:
        ...
```

## 9.7 RAG 与 Context 集成

```text
ContextAssembler
→ detect skill.memory/read or skill.rag enabled
→ build RetrievalQuery from task.goal
→ Retriever.retrieve
→ GroundingFormatter.format(results)
→ inject into PromptEngine variables
```

Prompt 变量：

```yaml
retrieved_context:
  type: rag_context
  source: rag.retrieve
  limit: 5
```

---

# 10. Memory 二期设计

## 10.1 目标

从 Summary Memory 扩展为完整 Memory System：

```text
Summary Memory
Semantic Memory
Entity Memory
Episodic Memory
Memory Candidate
Memory Policy
Memory Conflict Resolution
Memory Consolidation
```

## 10.2 目录结构

```text
memory/
├── base.py
├── manager.py
├── schemas.py
├── policy.py
├── extractor.py
├── consolidation.py
├── conflict.py
├── retrieval.py
├── stores/
│   ├── summary.py
│   ├── semantic.py
│   ├── entity.py
│   └── episodic.py
├── backends/
│   ├── postgres.py
│   ├── pgvector.py
│   ├── qdrant.py
│   └── filesystem.py
└── policies/
    ├── write_policy.py
    ├── update_policy.py
    ├── forget_policy.py
    └── retrieval_policy.py
```

## 10.3 Memory Types

```python
MemoryType = Literal["summary", "semantic", "entity", "episodic"]

class MemoryItem(BaseModel):
    memory_id: str
    type: MemoryType
    content: str
    key: str | None = None
    embedding: list[float] | None = None
    confidence: float = 0.5
    source_task_id: str | None = None
    source_event_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
```

## 10.4 MemoryCandidate

```python
class MemoryCandidate(BaseModel):
    type: MemoryType
    content: str
    key: str | None = None
    confidence: float
    reason: str
    source_task_id: str
    metadata: dict[str, Any] = Field(default_factory=dict)
```

## 10.5 Memory 写入流程

```text
TaskCompleted / SignificantObservation
→ MemoryExtractor generates candidates
→ MemoryPolicy evaluates
→ ConflictDetector checks existing memories
→ Optional human approval for low confidence or conflict
→ Write MemoryItem
→ Index if semantic
→ Emit MemoryWritten event
```

## 10.6 MemoryPolicy

```python
class MemoryPolicyDecision(BaseModel):
    allow_write: bool
    reason: str | None = None
    requires_review: bool = False
    target_store: str | None = None
    ttl_seconds: int | None = None
```

## 10.7 Entity Memory

Entity Memory 存储稳定事实：

```text
用户偏好
项目约定
代码规范
组织实体
任务上下文
```

```python
class EntityMemoryRecord(BaseModel):
    entity_type: str
    entity_id: str
    attribute: str
    value: str
    confidence: float
    source_memory_id: str
```

---

# 11. Sandbox 二期设计

## 11.1 目标

从开发期 subprocess runner 升级到 Docker sandbox。

能力：

```text
Docker Runner
Resource Limit
Network Policy
Filesystem Mount Policy
VFS Workspace Mount
Timeout
Stdout/Stderr Capture
Artifact Collection
```

## 11.2 目录结构

```text
sandbox/
├── base.py
├── manager.py
├── policy.py
├── resource_limits.py
├── network_policy.py
├── filesystem_policy.py
├── schemas.py
├── runners/
│   ├── subprocess.py
│   ├── docker.py
│   ├── python.py
│   └── browser.py
└── images/
    ├── python.Dockerfile
    └── node.Dockerfile
```

## 11.3 SandboxPolicy

```python
class SandboxPolicy(BaseModel):
    runner: Literal["subprocess", "docker"] = "docker"
    image: str = "agent-platform-python:latest"
    network: Literal["none", "allowlist", "full"] = "none"
    allowed_hosts: list[str] = Field(default_factory=list)
    read_paths: list[str] = Field(default_factory=list)
    write_paths: list[str] = Field(default_factory=list)
    cpu_limit: float = 1.0
    memory_limit_mb: int = 512
    timeout_seconds: int = 60
    env: dict[str, str] = Field(default_factory=dict)
```

## 11.4 Docker Runner

```python
class DockerSandboxRunner:
    async def run(self, request: SandboxRunRequest) -> SandboxRunResult:
        # 1. Create container with image
        # 2. Mount VFS workspace as read/write scoped volume
        # 3. Apply memory/cpu/time limits
        # 4. Apply network mode
        # 5. Execute command
        # 6. Capture stdout/stderr
        # 7. Collect artifacts
        # 8. Remove container
        ...
```

## 11.5 安全约束

```text
1. 默认 network=none。
2. 默认只挂载 /workspace/{task_id}。
3. 默认不注入 secrets。
4. 写入只能发生在 /workspace 或 /artifacts。
5. 容器结束后销毁。
6. 所有执行事件写入 audit。
```

---

# 12. Policy 二期设计

## 12.1 目标

从简单 YAML 规则升级为统一 Policy Engine。

策略覆盖：

```text
Tool Policy
Model Policy
Memory Policy
Sandbox Policy
Connector Policy
Prompt Policy
Data Access Policy
Approval Policy
```

## 12.2 目录结构

```text
policy/
├── __init__.py
├── engine.py
├── language.py
├── evaluator.py
├── rules.py
├── context.py
├── decisions.py
├── registry.py
├── compiler.py
├── schemas.py
└── builtin/
    ├── tool_policy.yaml
    ├── memory_policy.yaml
    ├── sandbox_policy.yaml
    ├── model_policy.yaml
    └── connector_policy.yaml
```

## 12.3 PolicyContext

```python
class PolicyContext(BaseModel):
    subject: dict[str, Any] = Field(default_factory=dict)
    action: str
    resource: dict[str, Any] = Field(default_factory=dict)
    environment: dict[str, Any] = Field(default_factory=dict)
    task: dict[str, Any] = Field(default_factory=dict)
    skill: dict[str, Any] = Field(default_factory=dict)
```

## 12.4 PolicyDecision

```python
class PolicyDecision(BaseModel):
    allowed: bool
    reason: str | None = None
    requires_approval: bool = False
    obligations: list[dict[str, Any]] = Field(default_factory=list)
    modified_context: dict[str, Any] = Field(default_factory=dict)
```

## 12.5 Policy DSL v0

YAML 规则：

```yaml
name: tool_policy
version: 0.2.0
rules:
  - id: deny_high_risk_without_approval
    when:
      action: tool.call
      resource.risk_level: high
    then:
      allowed: false
      requires_approval: true
      reason: high risk tool requires approval

  - id: allow_low_risk_tools
    when:
      action: tool.call
      resource.risk_level: low
    then:
      allowed: true
```

## 12.6 PolicyEngine

```python
class PolicyEngine:
    async def evaluate(self, policy_name: str, context: PolicyContext) -> PolicyDecision:
        policy = await self.registry.get(policy_name)
        for rule in policy.rules:
            if self.evaluator.matches(rule.when, context):
                return PolicyDecision(**rule.then)
        return PolicyDecision(allowed=False, reason="no matching policy rule")
```

---

# 13. Governance 二期设计

## 13.1 目标

补齐生产治理能力：

```text
Risk Classifier
Human Approval
Audit Log
Secret Scope
Guardrails
Compliance Rules
```

## 13.2 目录结构

```text
governance/
├── risk_classifier.py
├── guardrails.py
├── approvals.py
├── human_review.py
├── secrets.py
├── scopes.py
├── compliance.py
├── audit.py
└── schemas.py
```

## 13.3 ApprovalRequest

```python
class ApprovalRequest(BaseModel):
    approval_id: str
    task_id: str
    requested_by: str
    action: str
    resource: dict[str, Any]
    reason: str
    status: Literal["pending", "approved", "rejected", "expired"] = "pending"
    expires_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
```

## 13.4 Approval Flow

```text
PolicyDecision.requires_approval = true
→ Governance creates ApprovalRequest
→ Runtime status = waiting_human
→ Notification sent
→ Human approves/rejects via API/CLI
→ Runtime resumes or fails
```

## 13.5 Secrets

二期支持 secret scope：

```text
secret_ref = secret://github/token/default
```

Secret 永不进入：

```text
Prompt
Event payload
Logs
Artifact
Memory
```

仅在 connector/tool 执行时注入运行时内存。

---

# 14. Evaluation 二期设计

## 14.1 目标

虽然 Eval 不是 MVP 阻塞项，二期需要补齐质量闭环。

能力：

```text
Replay Debug
Trajectory Evaluation
Tool Call Evaluation
Final Answer Evaluation
Safety Evaluation
Cost Evaluation
Regression Dataset
Scorers
Eval Report
```

## 14.2 目录结构

```text
evaluation/
├── __init__.py
├── runner.py
├── dataset.py
├── replay.py
├── trajectory.py
├── tool_eval.py
├── answer_eval.py
├── safety_eval.py
├── cost_eval.py
├── regression.py
├── scorers.py
├── report.py
└── schemas.py
```

## 14.3 EvalDataset

```python
class EvalCase(BaseModel):
    case_id: str
    name: str
    input: dict[str, Any]
    expected: dict[str, Any] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

class EvalDataset(BaseModel):
    dataset_id: str
    name: str
    version: str
    cases: list[EvalCase]
```

## 14.4 EvalRun

```python
class EvalRun(BaseModel):
    eval_run_id: str
    dataset_id: str
    target: dict[str, Any]
    status: Literal["created", "running", "completed", "failed"]
    scores: dict[str, float] = Field(default_factory=dict)
    report_path: str | None = None
```

## 14.5 Trajectory Evaluation

输入：Runtime events。

指标：

```text
task_completed
max_steps_exceeded
tool_error_rate
invalid_tool_call_rate
policy_block_count
cost_usd
time_to_complete
unnecessary_tool_calls
memory_write_quality
```

## 14.6 Replay Debug

```text
GET /v1/tasks/{task_id}/replay
→ events.replay(task_id)
→ reconstruct timeline
→ show model/tool/memory/policy spans
```

---

# 15. Experiments 二期设计

## 15.1 目标

支持基础实验：

```text
Prompt A/B
Model A/B
Routing Strategy A/B
Memory Policy A/B
Tool Selection A/B
```

## 15.2 目录结构

```text
experiments/
├── experiment.py
├── variants.py
├── assignment.py
├── metrics.py
├── analysis.py
├── rollout.py
└── schemas.py
```

## 15.3 ExperimentDefinition

```python
class ExperimentVariant(BaseModel):
    variant_id: str
    weight: float
    config: dict[str, Any]

class ExperimentDefinition(BaseModel):
    experiment_id: str
    name: str
    target_type: Literal["prompt", "model", "routing", "memory_policy", "tool_policy"]
    status: Literal["draft", "running", "paused", "completed"]
    variants: list[ExperimentVariant]
    metrics: list[str]
```

## 15.4 Assignment

MVP+二期：hash-based assignment。

```python
variant = hash(user_id + experiment_id) % 100
```

---

# 16. Notifications 二期设计

## 16.1 目标

支持任务状态通知、审批通知、失败告警、外部回调。

## 16.2 目录结构

```text
notifications/
├── manager.py
├── channels.py
├── templates.py
├── subscriptions.py
├── webhooks.py
├── delivery.py
├── retry.py
└── providers/
    ├── webhook.py
    ├── slack.py
    ├── email.py
    └── in_app.py
```

## 16.3 NotificationEvent

```python
class NotificationEvent(BaseModel):
    notification_id: str
    type: str
    task_id: str | None = None
    recipient: str | None = None
    channel: Literal["webhook", "slack", "email", "in_app"]
    payload: dict[str, Any]
    status: Literal["pending", "sent", "failed"] = "pending"
```

## 16.4 触发点

```text
ApprovalRequestCreated
TaskCompleted
TaskFailed
EvalRunCompleted
PolicyViolation
SandboxViolation
```

---

# 17. Control Plane 二期设计

## 17.1 目标

提供平台管理 API，不做 Web UI 也能完整管理资源。

管理对象：

```text
Agent
Skill
Prompt
Tool
Connector
Policy
Workflow
Deployment
Memory
Eval Dataset
Plugin
```

## 17.2 目录结构

```text
control_plane/
├── service.py
├── agents.py
├── skills.py
├── tools.py
├── prompts.py
├── policies.py
├── workflows.py
├── connectors.py
├── memory.py
├── evals.py
├── deployments.py
├── plugins.py
└── schemas.py
```

## 17.3 API 设计

```text
GET    /v1/control/skills
POST   /v1/control/skills
POST   /v1/control/skills/reload

GET    /v1/control/prompts
POST   /v1/control/prompts
POST   /v1/control/prompts/render

GET    /v1/control/policies
POST   /v1/control/policies
POST   /v1/control/policies/test

GET    /v1/control/workflows
POST   /v1/control/workflows

GET    /v1/control/deployments
POST   /v1/control/deployments/releases
POST   /v1/control/deployments/{id}/activate
POST   /v1/control/deployments/{id}/rollback
```

---

# 18. Deployment 二期设计

## 18.1 目标

从简单 lockfile 升级到 release 管理。

支持：

```text
Release
Environment
Lockfile
Rollout
Rollback
Version Freeze
Diff
Validation
```

## 18.2 目录结构

```text
deployment/
├── package.py
├── release.py
├── environment.py
├── rollout.py
├── rollback.py
├── version.py
├── manifest.py
├── lockfile.py
├── diff.py
├── validator.py
└── schemas.py
```

## 18.3 ReleaseManifest

```python
class ReleaseManifest(BaseModel):
    release_id: str
    version: str
    environment: str
    skills: dict[str, str]
    prompts: dict[str, str]
    policies: dict[str, str]
    workflows: dict[str, str] = Field(default_factory=dict)
    tools: dict[str, str] = Field(default_factory=dict)
    created_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)
```

## 18.4 Deployment Flow

```text
Create ReleaseManifest
→ Validate all referenced versions exist
→ Validate prompt/skill/policy compatibility
→ Generate lockfile
→ Activate release for environment
→ Runtime resolves versions via active release
```

## 18.5 Rollback

```text
POST /v1/control/deployments/{release_id}/rollback
→ find previous active release
→ activate previous release
→ emit DeploymentRolledBack
```

---

# 19. Plugins 二期设计

## 19.1 目标

支持本地插件加载。插件可提供：

```text
Tool
Skill
Hook
Connector
Prompt Pack
Workflow
Policy
Model Adapter
```

## 19.2 目录结构

```text
plugins/
├── base.py
├── loader.py
├── manifest.py
├── registry.py
├── validator.py
├── sandbox.py
└── examples/
    ├── github_plugin/
    └── local_tools_plugin/
```

## 19.3 Plugin Manifest

```yaml
name: github_plugin
version: 0.1.0
entrypoint: github_plugin.main:register

provides:
  connectors:
    - github
  tools:
    - github.get_repo
    - github.create_issue
  skills:
    - github_triage
  hooks: []

permissions:
  network: true
  secrets:
    - github.token
```

## 19.4 Plugin Loader

```python
class PluginLoader:
    async def load(self, manifest_path: str) -> LoadedPlugin:
        # 1. Read manifest
        # 2. Validate schema
        # 3. Check permissions
        # 4. Import entrypoint
        # 5. Register provided components
        ...
```

## 19.5 安全限制

二期本地插件信任模型：

```text
1. 仅加载 allowlist 路径。
2. 插件 manifest 必须声明权限。
3. 插件提供的 tool 默认 risk_level=medium。
4. 插件 tool 必须经过 Tool Policy。
5. 插件不能直接读取 secrets，只能拿 secret_ref。
```

---

# 20. Artifacts 二期设计

## 20.1 目标

MVP 只有基础 VFS 产物保存。二期补齐 Artifact 生命周期。

## 20.2 目录结构

```text
artifacts/
├── manager.py
├── models.py
├── metadata.py
├── versioning.py
├── lineage.py
├── preview.py
├── export.py
├── retention.py
├── permissions.py
└── types/
    ├── report.py
    ├── code_patch.py
    ├── dataset.py
    ├── chart.py
    ├── notebook.py
    └── file.py
```

## 20.3 Artifact Model

```python
class Artifact(BaseModel):
    artifact_id: str
    task_id: str
    type: Literal["file", "report", "dataset", "chart", "code_patch", "notebook"]
    path: str
    version: int = 1
    metadata: dict[str, Any] = Field(default_factory=dict)
    lineage: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
```

## 20.4 Lineage

Artifact lineage 记录：

```text
source_task_id
source_step_id
source_tool_call_id
source_memory_ids
source_document_ids
prompt_version
skill_version
model_name
```

---

# 21. Storage 二期变更

## 21.1 新增表

```text
workflow_definitions
workflow_runs
workflow_step_runs
agent_cards
subagent_runs
connectors
connector_credentials
knowledge_documents
knowledge_chunks
memory_items_extended
vector_embeddings
approval_requests
policy_definitions
eval_datasets
eval_runs
experiments
notifications
releases
plugins
artifacts_extended
```

## 21.2 Vector Store

二期建议支持两种后端：

```text
pgvector：适合简单部署
Qdrant：适合专用向量服务
```

接口统一：

```python
class VectorStore(Protocol):
    async def upsert(self, items: list[VectorItem]) -> None:
        ...

    async def search(self, query_vector: list[float], limit: int, filters: dict[str, Any]) -> list[VectorSearchResult]:
        ...
```

---

# 22. API 二期扩展

## 22.1 Workflow API

```text
GET    /v1/workflows
POST   /v1/workflows
GET    /v1/workflows/{name}
POST   /v1/workflows/{name}/runs
GET    /v1/workflows/runs/{run_id}
```

## 22.2 Multi-Agent API

```text
GET    /v1/agents/cards
POST   /v1/agents/{agent_id}/delegate
GET    /v1/tasks/{task_id}/subagents
```

## 22.3 Knowledge / RAG API

```text
POST   /v1/knowledge/corpora
POST   /v1/knowledge/documents
GET    /v1/knowledge/documents/{document_id}
POST   /v1/knowledge/documents/{document_id}/ingest
POST   /v1/rag/retrieve
```

## 22.4 Memory API 扩展

```text
GET    /v1/memory/search
POST   /v1/memory/candidates
POST   /v1/memory/{memory_id}/approve
DELETE /v1/memory/{memory_id}
POST   /v1/memory/consolidate
```

## 22.5 Governance API

```text
GET    /v1/approvals
GET    /v1/approvals/{approval_id}
POST   /v1/approvals/{approval_id}/approve
POST   /v1/approvals/{approval_id}/reject
GET    /v1/audit/events
```

## 22.6 Evaluation API

```text
POST   /v1/evals/datasets
GET    /v1/evals/datasets
POST   /v1/evals/run
GET    /v1/evals/runs/{eval_run_id}
GET    /v1/evals/runs/{eval_run_id}/report
```

## 22.7 Deployment API

```text
POST   /v1/deployments/releases
GET    /v1/deployments/releases
GET    /v1/deployments/releases/{release_id}
POST   /v1/deployments/releases/{release_id}/activate
POST   /v1/deployments/releases/{release_id}/rollback
GET    /v1/deployments/diff?from=x&to=y
```

---

# 23. CLI 二期扩展

```bash
agent-platform workflows list
agent-platform workflows run research_workflow --input input.json

agent-platform knowledge ingest ./docs --corpus project-docs
agent-platform rag query "如何启动项目" --corpus project-docs

agent-platform memory search "用户偏好"
agent-platform memory consolidate

agent-platform approvals list
agent-platform approvals approve approval_123

agent-platform eval run general-agent-smoke
agent-platform eval report eval_123

agent-platform deploy create --manifest release.yaml
agent-platform deploy activate release_123
agent-platform deploy rollback

agent-platform plugins list
agent-platform plugins load ./plugins/github_plugin/plugin.yaml
```

---

# 24. 二期事件扩展

新增事件类型：

```text
WorkflowDefinitionRegistered
WorkflowRunCreated
WorkflowStepStarted
WorkflowStepCompleted
WorkflowStepFailed
WorkflowRunCompleted

SubAgentCreated
SubAgentStarted
SubAgentCompleted
SubAgentFailed
SubAgentResultMerged

ConnectorRegistered
ConnectorCallStarted
ConnectorCallCompleted
ConnectorCallFailed

KnowledgeDocumentCreated
KnowledgeDocumentIngested
KnowledgeChunkCreated
KnowledgeIndexed

RAGRetrieved
GroundingInjected

MemoryCandidateGenerated
MemoryConflictDetected
MemoryApproved
MemoryRejected
MemoryConsolidated

SandboxRunStarted
SandboxRunCompleted
SandboxViolationDetected

PolicyEvaluated
ApprovalRequestCreated
ApprovalApproved
ApprovalRejected

EvalRunCreated
EvalCaseCompleted
EvalRunCompleted

NotificationCreated
NotificationDelivered
NotificationFailed

DeploymentReleaseCreated
DeploymentActivated
DeploymentRolledBack

PluginLoaded
PluginRejected
```

---

# 25. 二期执行链路示例

## 25.1 多智能体 + RAG + 工具执行

```text
POST /v1/tasks
goal = "阅读项目文档并生成架构改进建议"

1. Runtime 创建 Task
2. SkillResolver 选择 general 或 architecture_review skill
3. WorkflowEngine 加载 review_workflow
4. Knowledge/RAG 检索项目文档
5. SupervisorAgent 创建子任务：
   - ResearchAgent：读取文档并总结
   - CriticAgent：分析风险
   - WriterAgent：生成建议报告
6. Subagents 通过隔离 context 执行
7. ToolRouter 调用 vfs/read、rag.retrieve、possibly connector
8. Results 聚合
9. Reflection 验证报告
10. ArtifactManager 保存 report.md
11. MemoryExtractor 生成 memory candidates
12. Policy 决定是否写入 memory
13. Evaluation 记录 trajectory metrics
14. Notification 发送完成通知
```

---

# 26. 二期测试设计

## 26.1 Unit Tests

```text
tests/unit/
├── test_workflow_runner.py
├── test_workflow_conditions.py
├── test_workflow_retry.py
├── test_multi_agent_delegation.py
├── test_subagent_isolation.py
├── test_connector_registry.py
├── test_knowledge_ingestion.py
├── test_rag_retriever.py
├── test_semantic_memory.py
├── test_entity_memory.py
├── test_docker_sandbox_policy.py
├── test_policy_engine.py
├── test_approval_flow.py
├── test_eval_runner.py
├── test_deployment_release.py
└── test_plugin_loader.py
```

## 26.2 Integration Tests

```text
tests/integration/
├── test_workflow_task_execution.py
├── test_multi_agent_task.py
├── test_rag_context_injection.py
├── test_memory_candidate_write.py
├── test_docker_sandbox_tool.py
├── test_policy_approval_runtime_resume.py
├── test_control_plane_deployment.py
├── test_plugin_tool_registration.py
└── test_eval_regression_run.py
```

## 26.3 E2E Tests

```text
tests/e2e/
├── test_general_agent_with_rag.py
├── test_general_agent_with_multi_agent.py
├── test_agent_generates_artifact.py
├── test_agent_requires_approval.py
└── test_release_rollback.py
```

---

# 27. 二期开发顺序

## Sprint 1：Workflow + Deployment 基础增强

目标：让 Agent 任务可通过 workflow 可靠执行。

交付：

```text
workflow definition / runner / state
workflow events
release manifest
deployment validation
workflow API / CLI
```

## Sprint 2：Multi-Agent 完整化

目标：支持 Supervisor + Subagent。

交付：

```text
AgentCard 扩展
SubAgentContext
Hierarchical orchestrator
Role agents
Result collection
Context isolation
A2A internal bus 增强
```

## Sprint 3：Connectors + Plugin 基础

目标：外部系统可扩展接入。

交付：

```text
connector registry
http connector
github connector
postgres connector
plugin manifest
local plugin loader
connector tools
```

## Sprint 4：Knowledge + RAG

目标：支持知识摄取和检索增强。

交付：

```text
knowledge document / chunk
markdown/text/html parser
embedding interface
vector store interface
retriever
grounding formatter
RAG context injection
```

## Sprint 5：Advanced Memory

目标：支持 semantic/entity/episodic memory。

交付：

```text
memory candidate
semantic memory store
entity memory store
episodic memory store
conflict detector
memory policy
memory consolidation
```

## Sprint 6：Docker Sandbox + Governance

目标：高风险工具可隔离执行并可审批。

交付：

```text
docker runner
sandbox policy
network/filesystem/cpu/memory limits
approval request
runtime waiting_human/resume
secret scope
audit enhancement
```

## Sprint 7：Evaluation + Notifications

目标：形成质量闭环和通知机制。

交付：

```text
eval dataset
eval runner
trajectory evaluator
tool evaluator
answer evaluator
regression runner
webhook/slack notification
approval notification
```

## Sprint 8：Control Plane 完整 API

目标：资源管理平台化。

交付：

```text
control API for skill/prompt/policy/workflow/deployment/plugin
release diff
rollback
resource validation
admin CLI
```

---

# 28. 二期 Definition of Done

二期完成标准：

```text
1. WorkflowEngine 支持 DAG、条件、重试、失败补偿基础能力。
2. MultiAgent 支持 Supervisor + 至少 3 类 Role Agent。
3. Subagent 具备 context/tool/memory/vfs 隔离。
4. Connectors 支持 HTTP、GitHub、PostgreSQL、Webhook/Slack。
5. Knowledge 支持文档摄取、切分、索引、元数据和来源追踪。
6. RAG 支持 retrieve + citation + grounding injection。
7. Memory 支持 summary、semantic、entity、episodic。
8. Docker sandbox 可执行 Python 任务并限制网络、文件和资源。
9. PolicyEngine 支持 YAML 规则、PolicyContext、PolicyDecision。
10. Governance 支持审批流、审计、secret scope。
11. Evaluation 支持 trajectory/tool/answer/regression 基础评估。
12. Notifications 支持 webhook/slack 基础通知。
13. Deployment 支持 release、activate、rollback、diff。
14. Plugins 支持本地插件加载并注册 tool/skill/hook/connector。
15. Control Plane API 可管理 skill、prompt、policy、workflow、deployment、plugin。
16. 所有二期新能力均写入 RuntimeEvent。
17. 核心二期模块单元测试覆盖率 >= 80%。
18. 新增 E2E 测试覆盖：multi-agent、rag、docker sandbox、approval、deployment rollback。
```

---

# 29. 风险与应对

| 风险 | 说明 | 应对 |
|---|---|---|
| 二期范围过大 | 涵盖几乎所有剩余平台能力 | 按 Sprint 切分，每个 Sprint 可独立上线 |
| Multi-Agent 调试复杂 | 子 Agent 上下文与结果难排查 | 所有子 Agent 独立 trace/span/event |
| Memory 污染 | 长期记忆写错会影响后续任务 | MemoryCandidate + Policy + Confidence + Review |
| RAG 质量不稳定 | 检索错误影响回答 | Citation + Grounding + Retriever metrics |
| Docker 安全边界不足 | 容器不是强隔离 | 默认无网络、只挂载 scoped workspace，Firecracker 留 Phase 3 |
| Policy DSL 复杂化 | 策略语言容易变成新系统 | 二期仅 YAML 条件匹配，不做复杂解释器 |
| Plugin 安全 | 插件可执行任意代码 | 本地 allowlist + manifest permission + tool policy |
| Evaluation 成本 | Eval 会带来额外模型调用 | 支持 mock scorer + sampling |
| Deployment 兼容 | Prompt/Skill/Policy 版本组合不兼容 | Release validation + compatibility check |

---

# 30. 二期与后续三期边界

二期完成后，平台基本具备完整产品形态。

三期更偏企业级与规模化：

```text
完整多租户隔离
计费与 quota
Firecracker / remote sandbox cluster
Plugin marketplace
Web control plane UI
分布式 worker queue
高级 ABAC
高级实验平台
长期任务 orchestration
跨 Agent 组织级协作
```

---

## 31. 结论

二期基本就是 MVP 之后的剩余功能开发，但不是简单堆模块，而是围绕四个目标展开：

```text
1. 执行更强：Workflow + Multi-Agent + Sandbox
2. 知识更强：Knowledge + RAG + Advanced Memory
3. 治理更强：Policy + Governance + Approval + Audit
4. 平台更强：Control Plane + Deployment + Plugins + Evaluation
```

二期完成后，Agent Platform 将从：

```text
可运行的通用 Agent Runtime
```

升级为：

```text
可扩展、可治理、可评估、可部署的 Agent Platform
```

这将覆盖 PRD 中除企业级多租户、计费、远程沙箱集群、插件市场和 Web UI 之外的大部分核心能力。

