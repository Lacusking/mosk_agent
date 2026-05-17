# 自研 Agent Platform 三期低层设计文档（Phase 3 LLD）

版本：v0.1  
状态：Draft  
目标实现语言：Python 3.12+  
依赖基线：MVP LLD v0.1、Phase 2 LLD v0.1  
阶段定位：企业级、规模化、商业化、多租户生产部署能力建设

---

## 1. 文档目的

本文档定义 Agent Platform 三期的低层设计。

一期目标：

```text
可运行的通用 Agent Runtime
```

二期目标：

```text
可扩展、可治理、可评估、可部署的 Agent Platform
```

三期目标：

```text
企业级、多租户、可商业化、可规模化运行的 Agent Operating Platform
```

三期不是继续补基础功能，而是围绕以下能力展开：

```text
1. 多租户隔离
2. Quota 与 Billing
3. 分布式 Worker 与任务调度
4. 远程 Sandbox 集群
5. Plugin / Skill / Tool Marketplace
6. Web Control Plane UI
7. 高级 Policy / ABAC / Compliance
8. 企业级安全与 Secret Management
9. 长期任务与 Durable Execution
10. 高级实验平台
11. SRE / HA / Disaster Recovery
12. 企业集成与组织级协作
```

---

## 2. 三期总体目标

### 2.1 一句话目标

将二期 Agent Platform 升级为支持多租户、计费、配额、插件市场、远程沙箱、Web 控制台、分布式执行、高级治理和企业级运维的生产级平台。

### 2.2 三期核心变化

| 维度 | 二期状态 | 三期目标 |
|---|---|---|
| 租户 | 单租户 / 轻量 project isolation | 完整 tenant / org / project 隔离 |
| 运行 | 单集群或单环境 worker | 分布式 worker pool + queue + lease |
| 沙箱 | Docker runner | Remote sandbox cluster / microVM 可选 |
| 计费 | cost tracking | quota / metering / billing / invoice |
| 插件 | 本地插件 | marketplace / 签名 / 信任等级 / 安装卸载 |
| 控制台 | API / CLI | Web Admin Console + Control Plane API |
| 策略 | YAML DSL | 高级 ABAC / policy simulation / policy audit |
| 安全 | secret scope 基础能力 | Secret Manager、KMS、审计、DLP、合规 |
| 实验 | 基础 A/B | 高级实验、灰度、自动分析、策略化 rollout |
| 可用性 | 基础部署 | HA、DR、备份恢复、SLO、容量治理 |
| 工作流 | workflow runner | durable long-running orchestration |
| 企业集成 | connectors | SSO、SCIM、审计导出、SIEM、企业知识源 |

---

## 3. 三期范围定义

## 3.1 三期必须完成

| 模块 | 目标 |
|---|---|
| tenancy / identity | 完整多租户、组织、项目、成员、角色、Service Account、SSO 预留 |
| quota | Token、模型调用、工具调用、沙箱时长、存储、向量检索、并发数限制 |
| billing | 用量计量、价格模型、账单生成、导出、成本归集 |
| distributed runtime | 分布式任务队列、worker lease、幂等、重试、死信队列 |
| remote sandbox | 独立 sandbox worker cluster，支持 Docker / microVM 接口 |
| marketplace | 插件、Skill、Tool、Workflow、Prompt Pack 的发布、安装、签名、版本管理 |
| web console | 管理 Agent、Skill、Tool、Prompt、Policy、Workflow、Eval、Deployment、Usage |
| advanced policy | ABAC、条件策略、策略模拟、策略测试、策略审计 |
| compliance | 审计导出、数据保留、删除、DLP、PII 检测、合规报告 |
| durable execution | 长周期任务、暂停恢复、外部事件唤醒、workflow signal |
| advanced experiments | 实验分析、显著性、自动 rollout、kill switch |
| sre platform | health、readiness、SLO、backup、restore、capacity、multi-env deployment |

## 3.2 三期可选或预留

| 能力 | 处理方式 |
|---|---|
| Firecracker microVM | 提供 runner interface，是否实现取决于安全需求 |
| BYOC 私有云部署 | 预留 Helm/Terraform，三期可实现基础版 |
| 多区域部署 | 设计支持，不一定完成跨 region active-active |
| 完整 SCIM | 预留接口，可先实现手动组织成员管理 |
| 企业合同计费 | Billing 保留 enterprise plan，先支持 metering/export |
| 插件收益分成 | Marketplace 预留 payment 字段，三期不强制实现 |
| 完整 SOC2/ISO 流程 | 工程接口支持，流程合规不在代码范围内 |

---

## 4. 三期新增与增强目录

在原目录基础上，三期建议新增以下顶层模块：

```text
src/agent_platform/
├── tenancy/             # 多租户隔离、组织、项目、资源边界
├── quota/               # 配额、限流、并发控制、资源限制
├── billing/             # 计量、价格、账单、成本归集
├── marketplace/         # 插件/Skill/Tool/Prompt/Workflow 市场
├── admin_console/       # Web 控制台后端 API 与前端应用接口适配，可放 apps/ 下
├── durable/             # 长期任务、signal、pause/resume、durable workflow state
├── sandbox_cluster/     # 远程沙箱调度、worker、镜像、资源池
├── data_governance/     # 数据保留、删除、DLP、PII、数据分类
├── compliance/          # 合规报告、审计导出、策略证明
├── sre/                 # 健康检查、SLO、容量、备份恢复、运维任务
└── enterprise/          # SSO、SCIM、SIEM、企业集成适配
```

也可以将部分模块合并进现有模块。推荐边界：

| 新能力 | 推荐位置 |
|---|---|
| tenant/org/project isolation | `tenancy/` + `identity/` |
| quota enforcement | `quota/` + `policy/` + `runtime/` hooks |
| billing metering | `billing/` + `observability/` |
| marketplace | `marketplace/` + `plugins/` + `deployment/` |
| remote sandbox | `sandbox_cluster/` + `sandbox/` |
| durable workflow | `durable/` + `workflow/` + `runtime/` |
| admin web | `apps/admin_console/` 或 `admin_console/` |
| data governance | `data_governance/` + `governance/` |
| SRE | `sre/` + `observability/` |

---

## 5. 三期目标架构

### 5.1 架构分层

```text
Web Admin Console / API / CLI / SDK / A2A / MCP
  ↓
Access / Identity / Tenancy / Quota
  ↓
Control Plane / Deployment / Marketplace
  ↓
Distributed Runtime / Durable Execution / Scheduler
  ↓
Skill / Prompt / Hook / Pattern / Workflow / Multi-Agent
  ↓
Tool / Connector / MCP / A2A / Remote Sandbox Cluster
  ↓
Context / Memory / Knowledge / RAG / Artifacts / VFS
  ↓
Policy / Governance / Compliance / Data Governance
  ↓
Observability / Evaluation / Experiments / Billing / SRE
  ↓
Storage / Queue / Object Store / Vector Store / Secret Store
```

### 5.2 三期主执行链路

```text
Request
→ Authenticate
→ Resolve Tenant / Org / Project
→ Enforce Quota
→ Resolve Active Deployment
→ Runtime Creates Durable Task
→ Queue Dispatches Task to Worker
→ Worker Acquires Lease
→ Skill / Workflow / Agent Resolve
→ Context / Memory / RAG Assemble with Tenant Scope
→ Model / Tool / Sandbox / Connector Execution
→ Meter Usage
→ Emit Events / Audit / Trace
→ Evaluate / Experiment Attribution
→ Persist Artifact / Memory
→ Update Quota / Billing Ledger
→ Notify / Webhook / Console Timeline
```

---

# 6. Tenancy 多租户设计

## 6.1 目标

三期需要将单租户平台升级为完整多租户平台。

核心要求：

```text
1. 所有资源必须归属 tenant_id。
2. 组织、项目、环境作为租户下级资源。
3. Runtime、Memory、VFS、Artifacts、Knowledge、Events、Billing 都必须 tenant-scoped。
4. 所有 API 必须进行 tenant resolution。
5. 所有存储查询必须带 tenant filter。
6. 插件、Skill、Tool、Prompt、Policy 可以是 global 或 tenant-local。
```

## 6.2 目录结构

```text
tenancy/
├── __init__.py
├── tenant.py
├── organization.py
├── project.py
├── environment.py
├── resource_scope.py
├── isolation.py
├── resolver.py
├── guards.py
├── schemas.py
└── repository.py
```

## 6.3 核心 Schema

```python
class Tenant(BaseModel):
    tenant_id: str
    name: str
    status: Literal["active", "suspended", "deleted"] = "active"
    plan_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

class Organization(BaseModel):
    org_id: str
    tenant_id: str
    name: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

class Project(BaseModel):
    project_id: str
    tenant_id: str
    org_id: str | None = None
    name: str
    status: Literal["active", "archived"] = "active"
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

class Environment(BaseModel):
    environment_id: str
    tenant_id: str
    project_id: str
    name: Literal["dev", "staging", "prod"]
    active_release_id: str | None = None
```

## 6.4 ResourceScope

```python
class ResourceScope(BaseModel):
    tenant_id: str
    org_id: str | None = None
    project_id: str | None = None
    environment_id: str | None = None
    visibility: Literal["private", "project", "tenant", "global"] = "project"
```

## 6.5 Tenant Resolution

```text
API Key / JWT / Session
→ Identity Resolver
→ Tenant Resolver
→ Project Resolver
→ AccessContext
→ RuntimeContext
```

## 6.6 存储隔离策略

MVP/二期表中新增或强制使用：

```text
tenant_id
project_id
environment_id
```

Repository 规则：

```python
async def get_task(task_id: str, scope: ResourceScope) -> Task:
    return await db.fetch_one(
        select(TaskModel).where(
            TaskModel.task_id == task_id,
            TaskModel.tenant_id == scope.tenant_id,
        )
    )
```

禁止：

```text
任何不带 tenant_id 的跨租户资源查询。
```

---

# 7. Identity 企业级增强

## 7.1 目标

在二期 Identity/RBAC 基础上支持企业级身份能力。

能力：

```text
User
Group
Role
Permission
Service Account
API Key
SSO Provider
SCIM 预留
Session Management
Audit Identity Actions
```

## 7.2 identity 目录增强

```text
identity/
├── users.py
├── groups.py
├── tenants.py
├── organizations.py
├── projects.py
├── roles.py
├── permissions.py
├── api_keys.py
├── service_accounts.py
├── sessions.py
├── auth_providers.py
├── rbac.py
├── abac.py
├── sso.py
├── scim.py
└── schemas.py
```

## 7.3 权限模型

```python
class Permission(BaseModel):
    action: str
    resource_type: str
    conditions: dict[str, Any] = Field(default_factory=dict)

class Role(BaseModel):
    role_id: str
    tenant_id: str
    name: str
    permissions: list[Permission]

class Membership(BaseModel):
    user_id: str
    tenant_id: str
    org_id: str | None = None
    project_id: str | None = None
    roles: list[str]
```

## 7.4 标准角色

```text
owner
admin
developer
operator
viewer
billing_admin
security_admin
```

## 7.5 Service Account

```python
class ServiceAccount(BaseModel):
    service_account_id: str
    tenant_id: str
    name: str
    roles: list[str]
    scopes: list[str]
    expires_at: datetime | None = None
```

用途：

```text
CI/CD 部署
Webhook 调用
外部系统集成
后台任务
```

---

# 8. Quota 配额系统设计

## 8.1 目标

控制资源使用，防止成本失控。

配额维度：

```text
Token
Model calls
Tool calls
Sandbox execution seconds
Concurrent tasks
Concurrent sandbox runs
Storage bytes
Artifact bytes
Vector documents / chunks
RAG retrieval calls
MCP calls
A2A calls
Workflow runs
```

## 8.2 目录结构

```text
quota/
├── __init__.py
├── limits.py
├── usage.py
├── enforcement.py
├── reservations.py
├── rate_limit.py
├── concurrency.py
├── plans.py
├── schemas.py
└── repository.py
```

## 8.3 QuotaLimit

```python
class QuotaLimit(BaseModel):
    limit_id: str
    tenant_id: str
    metric: str
    period: Literal["minute", "hour", "day", "month", "lifetime"]
    limit: float
    hard: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)
```

## 8.4 UsageRecord

```python
class UsageRecord(BaseModel):
    usage_id: str
    tenant_id: str
    project_id: str | None = None
    task_id: str | None = None
    metric: str
    quantity: float
    unit: str
    source: str
    created_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)
```

## 8.5 Quota Enforcement Flow

```text
before_task_start
→ check concurrent_tasks
→ reserve estimated token / sandbox / task budget

before_model_call
→ check token monthly quota
→ reserve estimated input/output tokens

after_model_call
→ record actual token usage
→ release unused reservation

before_tool_call
→ check tool call quota

after_sandbox_exec
→ record sandbox seconds
```

## 8.6 QuotaEnforcer

```python
class QuotaEnforcer:
    async def check(self, tenant_id: str, metric: str, quantity: float) -> QuotaDecision:
        ...

    async def reserve(self, tenant_id: str, metric: str, quantity: float, ttl_seconds: int) -> Reservation:
        ...

    async def record(self, record: UsageRecord) -> None:
        ...
```

---

# 9. Billing 计费系统设计

## 9.1 目标

将 observability 中的 cost tracking 升级为商业化 billing。

能力：

```text
Usage Metering
Pricing Plan
Cost Attribution
Invoice Generation
Credit Balance
Usage Export
Billing Alerts
```

## 9.2 目录结构

```text
billing/
├── __init__.py
├── metering.py
├── pricing.py
├── plans.py
├── ledger.py
├── invoices.py
├── credits.py
├── attribution.py
├── export.py
├── alerts.py
├── schemas.py
└── repository.py
```

## 9.3 PricingPlan

```python
class PricingMetric(BaseModel):
    metric: str
    unit: str
    unit_price_usd: Decimal
    free_units: float = 0

class PricingPlan(BaseModel):
    plan_id: str
    name: str
    monthly_base_price_usd: Decimal = Decimal("0")
    metrics: list[PricingMetric]
    metadata: dict[str, Any] = Field(default_factory=dict)
```

## 9.4 BillingLedgerEntry

```python
class BillingLedgerEntry(BaseModel):
    entry_id: str
    tenant_id: str
    project_id: str | None = None
    task_id: str | None = None
    metric: str
    quantity: float
    unit_price_usd: Decimal
    amount_usd: Decimal
    source_usage_id: str
    created_at: datetime
```

## 9.5 Metering Flow

```text
UsageRecordCreated
→ MeteringService consumes event
→ Resolve tenant plan
→ Apply pricing metric
→ Create BillingLedgerEntry
→ Update monthly usage summary
```

## 9.6 Invoice

```python
class Invoice(BaseModel):
    invoice_id: str
    tenant_id: str
    period_start: datetime
    period_end: datetime
    status: Literal["draft", "issued", "paid", "void"]
    subtotal_usd: Decimal
    credits_usd: Decimal = Decimal("0")
    total_usd: Decimal
    line_items: list[dict[str, Any]]
```

三期可先不接真实支付网关，但必须支持：

```text
账单生成
CSV/JSON 导出
用量明细查询
项目级成本归集
```

---

# 10. Distributed Runtime 分布式运行设计

## 10.1 目标

将二期 runtime worker 升级为分布式 worker pool。

能力：

```text
Task Queue
Worker Lease
Retry
Dead Letter Queue
Idempotency
Distributed Lock
Backpressure
Priority Queue
Task Sharding
Worker Heartbeat
```

## 10.2 runtime / workers 增强

```text
runtime/
├── distributed.py
├── leases.py
├── idempotency.py
├── backpressure.py
└── priority.py

workers/
├── worker_app.py
├── runtime_worker.py
├── tool_worker.py
├── sandbox_worker.py
├── memory_worker.py
├── eval_worker.py
├── queue.py
├── lease.py
├── heartbeat.py
└── dead_letter.py
```

## 10.3 Queue Backend

三期支持可插拔队列：

```text
Redis Streams
PostgreSQL queue
RabbitMQ
Kafka / Redpanda 预留
```

接口：

```python
class QueueBackend(Protocol):
    async def enqueue(self, queue: str, message: QueueMessage) -> None:
        ...

    async def dequeue(self, queue: str, timeout_seconds: int) -> QueueMessage | None:
        ...

    async def ack(self, message_id: str) -> None:
        ...

    async def nack(self, message_id: str, reason: str) -> None:
        ...
```

## 10.4 QueueMessage

```python
class QueueMessage(BaseModel):
    message_id: str
    tenant_id: str
    task_id: str | None = None
    type: str
    priority: int = 100
    payload: dict[str, Any]
    idempotency_key: str | None = None
    created_at: datetime
    available_at: datetime | None = None
    attempts: int = 0
    max_attempts: int = 3
```

## 10.5 Worker Lease

```python
class WorkerLease(BaseModel):
    lease_id: str
    message_id: str
    worker_id: str
    expires_at: datetime
    heartbeat_at: datetime
```

流程：

```text
Worker dequeue message
→ acquire lease
→ execute
→ heartbeat periodically
→ ack on success
→ nack/retry on failure
→ DLQ after max attempts
```

## 10.6 Idempotency

所有外部副作用操作必须使用 idempotency key：

```text
tool_call:{task_id}:{step_id}:{tool_name}:{args_hash}
artifact_create:{task_id}:{path_hash}
billing_meter:{usage_id}
notification:{notification_id}
```

---

# 11. Durable Execution 长期任务设计

## 11.1 目标

支持长周期 Agent 与 Workflow：

```text
暂停
恢复
等待人工审批
等待外部 webhook
等待计划时间
等待另一个 agent 回调
signal / event 唤醒
checkpoint
version-safe resume
```

## 11.2 目录结构

```text
durable/
├── __init__.py
├── instance.py
├── checkpoint.py
├── signal.py
├── timer.py
├── wait_condition.py
├── resume.py
├── history.py
├── versioning.py
├── schemas.py
└── repository.py
```

## 11.3 DurableInstance

```python
class DurableInstance(BaseModel):
    instance_id: str
    tenant_id: str
    task_id: str
    workflow_run_id: str | None = None
    status: Literal["running", "waiting", "completed", "failed", "cancelled"]
    wait_type: Literal["none", "human", "webhook", "timer", "signal", "external_agent"] = "none"
    wait_condition: dict[str, Any] = Field(default_factory=dict)
    checkpoint_id: str | None = None
    version: str
    created_at: datetime
    updated_at: datetime
```

## 11.4 Signal

```python
class DurableSignal(BaseModel):
    signal_id: str
    tenant_id: str
    instance_id: str
    name: str
    payload: dict[str, Any]
    created_at: datetime
```

## 11.5 Runtime 集成

```text
Runtime detects WAITING_HUMAN / WAITING_WEBHOOK / WAITING_TIMER
→ DurableInstance.status = waiting
→ Release worker lease
→ Wait for signal
→ Signal received
→ Requeue task resume message
→ Runtime loads checkpoint and continues
```

---

# 12. Remote Sandbox Cluster 设计

## 12.1 目标

从单机 Docker runner 升级为远程沙箱集群。

能力：

```text
Sandbox Scheduler
Sandbox Worker
Image Registry
Resource Pool
Network Isolation
Workspace Sync
Artifact Sync
Log Streaming
microVM Runner Interface
Quota Integration
```

## 12.2 目录结构

```text
sandbox_cluster/
├── __init__.py
├── scheduler.py
├── worker.py
├── pool.py
├── image_registry.py
├── resource_manager.py
├── network.py
├── workspace_sync.py
├── artifact_sync.py
├── log_stream.py
├── lease.py
├── schemas.py
└── runners/
    ├── docker_remote.py
    ├── firecracker.py
    └── kubernetes_job.py
```

## 12.3 SandboxJob

```python
class SandboxJob(BaseModel):
    job_id: str
    tenant_id: str
    task_id: str
    tool_invocation_id: str
    runner: Literal["docker", "firecracker", "kubernetes_job"]
    image: str
    command: list[str]
    workspace_ref: str
    artifact_output_path: str | None = None
    policy: SandboxPolicy
    status: Literal["queued", "running", "completed", "failed", "cancelled"] = "queued"
    created_at: datetime
    updated_at: datetime
```

## 12.4 SandboxWorker

```python
class SandboxWorker:
    async def run_job(self, job: SandboxJob) -> SandboxJobResult:
        # 1. Pull image
        # 2. Sync workspace
        # 3. Start isolated execution
        # 4. Stream logs
        # 5. Enforce timeout/resource/network policy
        # 6. Sync artifacts
        # 7. Cleanup
        ...
```

## 12.5 Workspace Sync

```text
VFS workspace snapshot
→ upload to object store
→ sandbox worker downloads snapshot
→ execute
→ upload changed artifacts
→ ArtifactManager imports output
```

## 12.6 Security

```text
1. Per-job isolated container or microVM。
2. No shared writable volume across tenants。
3. Network default none。
4. Secret injection through short-lived env/file mount。
5. Logs redacted before persistence。
6. Sandbox job tied to quota and billing。
```

---

# 13. Marketplace 设计

## 13.1 目标

从本地插件加载升级为 marketplace。

支持资产类型：

```text
Plugin
Skill
Tool
Prompt Pack
Workflow
Policy Pack
Connector
Model Adapter
Sandbox Image
```

## 13.2 目录结构

```text
marketplace/
├── __init__.py
├── catalog.py
├── package.py
├── publisher.py
├── installer.py
├── verifier.py
├── signature.py
├── trust.py
├── reviews.py
├── permissions.py
├── dependency.py
├── versioning.py
├── repository.py
├── schemas.py
└── sources/
    ├── local.py
    ├── git.py
    ├── registry.py
    └── private_registry.py
```

## 13.3 MarketplacePackage

```python
class MarketplacePackage(BaseModel):
    package_id: str
    name: str
    version: str
    type: Literal["plugin", "skill", "tool", "prompt_pack", "workflow", "policy_pack", "connector"]
    publisher_id: str
    description: str | None = None
    manifest: dict[str, Any]
    signature: str | None = None
    checksum: str
    trust_level: Literal["unknown", "verified", "trusted", "internal"] = "unknown"
    permissions: list[str] = Field(default_factory=list)
    dependencies: list[dict[str, str]] = Field(default_factory=list)
    created_at: datetime
```

## 13.4 Install Flow

```text
User selects package
→ Fetch manifest
→ Verify checksum/signature
→ Analyze permissions
→ Resolve dependencies
→ Policy approval if high risk
→ Install into tenant namespace
→ Register provided assets
→ Create Deployment candidate
```

## 13.5 Trust Model

```text
internal      = 企业内部发布
trusted       = 平台认证发布者
verified      = 签名验证通过
unknown       = 未验证，默认限制权限
```

## 13.6 安装作用域

```text
global: 平台管理员安装，所有 tenant 可用
tenant: 某租户安装
project: 某项目安装
sandboxed: 只允许在沙箱内运行
```

---

# 14. Admin Console / Web Control Plane 设计

## 14.1 目标

二期 Control Plane 以 API/CLI 为主，三期增加 Web 控制台。

主要页面：

```text
Dashboard
Tasks
Sessions
Agents
Skills
Prompts
Tools
Workflows
Memory
Knowledge / RAG
Artifacts
Deployments
Marketplace
Policies
Approvals
Evaluations
Experiments
Usage / Billing
Audit Logs
Settings
```

## 14.2 推荐目录

前端可以独立在 `apps/admin_console/`：

```text
apps/admin_console/
├── package.json
├── src/
│   ├── app/
│   ├── pages/
│   ├── components/
│   ├── api/
│   ├── stores/
│   ├── routes/
│   └── styles/
└── vite.config.ts
```

后端适配：

```text
admin_console/
├── __init__.py
├── service.py
├── dashboard.py
├── timeline.py
├── usage.py
├── resource_tree.py
├── schemas.py
└── permissions.py
```

## 14.3 Dashboard API

```text
GET /v1/admin/dashboard/summary
GET /v1/admin/dashboard/usage
GET /v1/admin/dashboard/errors
GET /v1/admin/dashboard/recent-tasks
```

## 14.4 Task Timeline API

```text
GET /v1/admin/tasks/{task_id}/timeline
```

返回：

```python
class TimelineItem(BaseModel):
    timestamp: datetime
    event_type: str
    actor_type: str
    title: str
    summary: str
    span_id: str | None = None
    payload_preview: dict[str, Any] = Field(default_factory=dict)
```

---

# 15. Advanced Policy / ABAC 设计

## 15.1 目标

将二期 YAML 规则升级为高级策略系统。

能力：

```text
RBAC + ABAC
Policy Simulation
Policy Test Cases
Policy Audit
Policy Version Diff
Obligations
Deny Overrides
Data Classification Conditions
Quota-aware Policies
```

## 15.2 Policy DSL v1

```yaml
name: data_access_policy
version: 1.0.0
effect_strategy: deny_overrides
rules:
  - id: allow_project_member_read_project_artifacts
    effect: allow
    when:
      subject.roles.contains: developer
      action: artifact.read
      resource.project_id.equals: subject.project_id
      resource.classification.in:
        - public
        - internal

  - id: deny_sensitive_data_to_external_tool
    effect: deny
    when:
      action: tool.call
      resource.tool_category: external_connector
      context.data_classification: sensitive
    obligations:
      - type: audit
      - type: notify_security
```

## 15.3 ABAC Context

```python
class ABACSubject(BaseModel):
    user_id: str
    tenant_id: str
    roles: list[str]
    groups: list[str]
    attributes: dict[str, Any] = Field(default_factory=dict)

class ABACResource(BaseModel):
    resource_type: str
    resource_id: str
    tenant_id: str
    project_id: str | None = None
    owner_id: str | None = None
    classification: str = "internal"
    attributes: dict[str, Any] = Field(default_factory=dict)

class ABACContext(BaseModel):
    subject: ABACSubject
    action: str
    resource: ABACResource
    environment: dict[str, Any] = Field(default_factory=dict)
```

## 15.4 Policy Simulation API

```text
POST /v1/policies/{policy_name}/simulate
```

Request:

```json
{
  "subject": {"roles": ["developer"]},
  "action": "tool.call",
  "resource": {"tool_name": "github.create_issue"},
  "environment": {}
}
```

Response:

```json
{
  "allowed": true,
  "matched_rules": ["allow_project_tool"],
  "obligations": []
}
```

---

# 16. Data Governance / Compliance 设计

## 16.1 目标

支持企业数据治理。

能力：

```text
Data Classification
PII Detection
DLP Rule
Retention Policy
Right to Delete
Audit Export
Compliance Report
Data Lineage
Memory Redaction
Artifact Redaction
```

## 16.2 目录结构

```text
data_governance/
├── __init__.py
├── classification.py
├── pii.py
├── dlp.py
├── retention.py
├── deletion.py
├── lineage.py
├── redaction.py
├── scanners.py
├── schemas.py
└── repository.py

compliance/
├── __init__.py
├── audit_export.py
├── reports.py
├── evidence.py
├── controls.py
├── retention_jobs.py
└── schemas.py
```

## 16.3 DataClassification

```python
class DataClassification(BaseModel):
    resource_type: str
    resource_id: str
    classification: Literal["public", "internal", "confidential", "sensitive", "restricted"]
    labels: list[str] = Field(default_factory=list)
    detected_pii: list[str] = Field(default_factory=list)
    confidence: float = 1.0
    created_at: datetime
```

## 16.4 RetentionPolicy

```python
class RetentionPolicy(BaseModel):
    policy_id: str
    tenant_id: str
    resource_type: str
    retention_days: int
    action: Literal["delete", "archive", "redact"]
    conditions: dict[str, Any] = Field(default_factory=dict)
```

## 16.5 Delete Request

```text
DELETE /v1/data-subjects/{subject_id}
```

执行：

```text
Find memories / artifacts / events / knowledge documents containing subject_id
→ Redact or delete according to retention/compliance policy
→ Record ComplianceEvidence
```

注意：RuntimeEvent 可能需要不可变审计。对于事件中的敏感数据，推荐：

```text
事件 payload 写入前脱敏
已写入事件做 redaction overlay，不物理删除审计元数据
```

---

# 17. Enterprise Integrations 设计

## 17.1 目标

支持企业客户集成。

能力：

```text
SSO OIDC/SAML
SCIM user provisioning 预留
SIEM audit export
Enterprise Knowledge Connectors
Private Model Provider Config
Custom Domain / API Gateway 预留
```

## 17.2 目录结构

```text
enterprise/
├── __init__.py
├── sso/
│   ├── oidc.py
│   ├── saml.py
│   └── schemas.py
├── scim/
│   ├── users.py
│   ├── groups.py
│   └── schemas.py
├── siem/
│   ├── exporter.py
│   ├── splunk.py
│   ├── datadog.py
│   └── webhook.py
├── domains.py
├── private_models.py
└── schemas.py
```

## 17.3 SSO Provider

```python
class SSOProvider(BaseModel):
    provider_id: str
    tenant_id: str
    type: Literal["oidc", "saml"]
    name: str
    config: dict[str, Any]
    enabled: bool = True
```

## 17.4 SIEM Export

```text
AuditEvent
→ SIEMExporter
→ Splunk / Datadog / Webhook / S3 export
```

---

# 18. Advanced Experiments 设计

## 18.1 目标

二期 experiments 是基础 A/B，三期需要完整实验平台。

能力：

```text
Experiment Lifecycle
Traffic Allocation
Segmentation
Metrics Attribution
Statistical Analysis
Auto Rollout
Kill Switch
Guardrail Metrics
```

## 18.2 experiments 目录增强

```text
experiments/
├── experiment.py
├── variants.py
├── assignment.py
├── segmentation.py
├── metrics.py
├── analysis.py
├── significance.py
├── rollout.py
├── guardrails.py
├── kill_switch.py
└── schemas.py
```

## 18.3 ExperimentMetric

```python
class ExperimentMetric(BaseModel):
    name: str
    type: Literal["success", "cost", "latency", "quality", "safety"]
    direction: Literal["maximize", "minimize"]
    guardrail: bool = False
    threshold: float | None = None
```

## 18.4 Auto Rollout

```text
If variant improves primary metric
AND guardrail metrics not degraded
AND sample size sufficient
→ increase traffic allocation
```

Kill switch：

```text
If safety violation > threshold
OR cost > threshold
OR failure rate > threshold
→ disable experiment variant
```

---

# 19. SRE / Operations 设计

## 19.1 目标

支持生产运维。

能力：

```text
Health Check
Readiness Check
SLO / SLI
Capacity Metrics
Backup / Restore
Disaster Recovery
Migration Jobs
Operational Runbooks
Incident Events
```

## 19.2 目录结构

```text
sre/
├── __init__.py
├── health.py
├── readiness.py
├── slo.py
├── capacity.py
├── backup.py
├── restore.py
├── migrations.py
├── incidents.py
├── runbooks.py
├── maintenance.py
└── schemas.py
```

## 19.3 SLI 指标

```text
Task success rate
Task p50/p95/p99 latency
Model call success rate
Tool call success rate
Sandbox job success rate
Queue lag
Worker availability
Event write latency
API error rate
Cost per task
Token per task
```

## 19.4 SLO 示例

```yaml
slo:
  task_success_rate:
    target: 0.95
    window: 7d
  api_availability:
    target: 0.999
    window: 30d
  event_write_success:
    target: 0.9999
    window: 30d
```

## 19.5 Backup / Restore

备份对象：

```text
PostgreSQL
Object Store
Vector Store
Deployment releases
Marketplace packages
Secret metadata, not raw secrets unless KMS-backed
```

Restore 流程：

```text
Stop writes or enter maintenance mode
→ Restore DB snapshot
→ Restore object store snapshot
→ Rebuild vector indexes if needed
→ Validate releases
→ Resume workers
```

---

# 20. Storage 三期设计

## 20.1 新增表

```text
tenants
organizations
projects
environments
memberships
roles
permissions
service_accounts
api_keys
quota_limits
usage_records
quota_reservations
pricing_plans
billing_ledger
invoices
worker_leases
queue_messages
durable_instances
durable_signals
sandbox_jobs
sandbox_workers
marketplace_packages
package_installs
admin_audit_logs
data_classifications
retention_policies
deletion_requests
sso_providers
siem_exports
experiment_assignments
slo_definitions
backup_runs
restore_runs
```

## 20.2 数据库索引要求

所有主业务表必须包含：

```text
tenant_id index
project_id index if applicable
created_at index
task_id index for runtime-related tables
trace_id index for event-related tables
```

示例：

```sql
CREATE INDEX idx_tasks_tenant_created ON tasks (tenant_id, created_at DESC);
CREATE INDEX idx_events_tenant_task ON runtime_events (tenant_id, task_id, created_at ASC);
CREATE INDEX idx_usage_tenant_metric_period ON usage_records (tenant_id, metric, created_at DESC);
```

## 20.3 存储分层

```text
PostgreSQL: metadata, task, event, billing, policy
Object Store: artifacts, workspace snapshots, package blobs
Vector Store: embeddings, semantic memory, knowledge chunks
Redis: cache, rate limit, queue optional
Secret Store: encrypted secrets / KMS refs
```

---

# 21. API 三期扩展

## 21.1 Tenancy / Identity API

```text
POST   /v1/tenants
GET    /v1/tenants/{tenant_id}
POST   /v1/orgs
POST   /v1/projects
GET    /v1/projects
POST   /v1/memberships
GET    /v1/roles
POST   /v1/service-accounts
POST   /v1/api-keys
```

## 21.2 Quota / Billing API

```text
GET    /v1/usage/summary
GET    /v1/usage/records
GET    /v1/quota/limits
POST   /v1/quota/limits
GET    /v1/billing/ledger
GET    /v1/billing/invoices
POST   /v1/billing/invoices/generate
GET    /v1/billing/export
```

## 21.3 Sandbox Cluster API

```text
GET    /v1/sandbox/jobs
GET    /v1/sandbox/jobs/{job_id}
POST   /v1/sandbox/jobs/{job_id}/cancel
GET    /v1/sandbox/workers
GET    /v1/sandbox/images
POST   /v1/sandbox/images
```

## 21.4 Marketplace API

```text
GET    /v1/marketplace/packages
GET    /v1/marketplace/packages/{package_id}
POST   /v1/marketplace/packages
POST   /v1/marketplace/packages/{package_id}/install
POST   /v1/marketplace/packages/{package_id}/uninstall
GET    /v1/marketplace/installs
```

## 21.5 Durable Execution API

```text
GET    /v1/durable/instances
GET    /v1/durable/instances/{instance_id}
POST   /v1/durable/instances/{instance_id}/signal
POST   /v1/durable/instances/{instance_id}/cancel
POST   /v1/durable/instances/{instance_id}/resume
```

## 21.6 Compliance API

```text
GET    /v1/compliance/audit-export
POST   /v1/compliance/reports
GET    /v1/compliance/reports/{report_id}
POST   /v1/data-governance/classify
POST   /v1/data-governance/deletion-requests
GET    /v1/data-governance/retention-policies
POST   /v1/data-governance/retention-policies
```

## 21.7 SRE API

```text
GET    /v1/ops/health
GET    /v1/ops/readiness
GET    /v1/ops/slo
GET    /v1/ops/capacity
POST   /v1/ops/backups
GET    /v1/ops/backups/{backup_id}
POST   /v1/ops/restores
```

---

# 22. CLI 三期扩展

```bash
agent-platform tenants create acme
agent-platform projects create demo --tenant acme

agent-platform quota get --tenant acme
agent-platform quota set token.monthly 10000000 --tenant acme

agent-platform billing usage --tenant acme
agent-platform billing invoice generate --month 2026-05

agent-platform marketplace search github
agent-platform marketplace install github_plugin --tenant acme
agent-platform marketplace verify ./package.zip

agent-platform sandbox jobs list
agent-platform sandbox jobs logs job_123

agent-platform durable instances list
agent-platform durable signal instance_123 approval_granted '{"ok":true}'

agent-platform policy simulate data_access_policy --input input.json
agent-platform compliance audit-export --from 2026-05-01 --to 2026-05-31

agent-platform ops health
agent-platform ops backup create
agent-platform ops restore restore_123
```

---

# 23. 三期事件扩展

新增事件类型：

```text
TenantCreated
TenantSuspended
ProjectCreated
MembershipChanged
RoleAssigned
ServiceAccountCreated

QuotaChecked
QuotaExceeded
QuotaReserved
UsageRecorded
BillingLedgerEntryCreated
InvoiceGenerated

QueueMessageEnqueued
WorkerLeaseAcquired
WorkerHeartbeatMissed
MessageMovedToDLQ

DurableInstanceCreated
DurableInstanceWaiting
DurableSignalReceived
DurableInstanceResumed

SandboxJobQueued
SandboxJobStarted
SandboxJobLogEmitted
SandboxJobCompleted
SandboxJobFailed

MarketplacePackagePublished
MarketplacePackageVerified
MarketplacePackageInstalled
MarketplacePackageUninstalled
PluginSignatureFailed

PolicySimulated
PolicyAuditCreated
ABACDecisionEvaluated

DataClassified
PIIDetected
DLPViolationDetected
RetentionPolicyApplied
DeletionRequestCreated
DeletionRequestCompleted

SSOProviderConfigured
SIEMExportCompleted

ExperimentVariantAssigned
ExperimentGuardrailViolated
ExperimentRolledOut
ExperimentKilled

BackupStarted
BackupCompleted
RestoreStarted
RestoreCompleted
SLOViolationDetected
IncidentCreated
```

---

# 24. 三期安全设计

## 24.1 安全原则

```text
1. 默认 deny。
2. 租户隔离优先于功能便利。
3. Secret 只在执行时短时注入。
4. 所有外部副作用操作可审计。
5. 所有 marketplace 包需声明权限。
6. 高风险能力必须 approval 或 admin policy。
7. Sandbox 执行必须绑定 quota、tenant、task、policy。
8. PII 与敏感数据进入 Prompt 前必须经过治理策略。
```

## 24.2 Secret Store

Secret 不应保存在普通 DB 明文中。

设计：

```python
class SecretRef(BaseModel):
    secret_ref: str
    tenant_id: str
    name: str
    provider: Literal["env", "local_encrypted", "vault", "aws_secrets_manager", "gcp_secret_manager"]
    scope: ResourceScope
    metadata: dict[str, Any] = Field(default_factory=dict)
```

读取流程：

```text
Tool/Connector requests secret_ref
→ Policy checks permission
→ SecretManager loads secret
→ Inject into process memory only
→ Redact from logs/events
```

## 24.3 Marketplace 安全

```text
Manifest validation
Checksum verification
Signature verification
Permission review
Risk classification
Sandbox requirement
Tenant-scoped install
Audit install/uninstall
```

---

# 25. 三期部署架构

## 25.1 推荐部署组件

```text
API Server
Control Plane API
Runtime Workers
Tool Workers
Sandbox Workers
Memory Workers
Eval Workers
Notification Workers
Billing Workers
Scheduler
PostgreSQL
Redis / Queue
Object Store
Vector Store
Secret Store
OpenTelemetry Collector
Prometheus / Grafana
Admin Console
```

## 25.2 Kubernetes 资源

```text
Deployment: api-server
Deployment: control-plane
Deployment: runtime-worker
Deployment: tool-worker
Deployment: sandbox-worker
Deployment: billing-worker
Deployment: notification-worker
CronJob: retention-job
CronJob: billing-invoice-job
CronJob: backup-job
StatefulSet: postgres, redis, vector-store if self-hosted
Ingress: api, admin-console
ConfigMap: app config
Secret: runtime secrets
NetworkPolicy: sandbox isolation
```

## 25.3 Helm 目录

```text
infra/helm/agent-platform/
├── Chart.yaml
├── values.yaml
├── templates/
│   ├── api-deployment.yaml
│   ├── worker-deployment.yaml
│   ├── sandbox-worker.yaml
│   ├── admin-console.yaml
│   ├── ingress.yaml
│   ├── configmap.yaml
│   ├── secrets.yaml
│   ├── networkpolicy.yaml
│   └── cronjobs.yaml
```

---

# 26. 测试设计

## 26.1 Unit Tests

```text
tests/unit/
├── test_tenant_resolver.py
├── test_resource_scope.py
├── test_abac_policy.py
├── test_quota_enforcer.py
├── test_billing_metering.py
├── test_queue_backend.py
├── test_worker_lease.py
├── test_durable_signal.py
├── test_sandbox_cluster_scheduler.py
├── test_marketplace_signature.py
├── test_plugin_permission_review.py
├── test_data_classification.py
├── test_retention_policy.py
├── test_experiment_assignment.py
└── test_backup_restore_plan.py
```

## 26.2 Integration Tests

```text
tests/integration/
├── test_multi_tenant_task_isolation.py
├── test_quota_blocks_task.py
├── test_usage_to_billing_ledger.py
├── test_worker_lease_retry_dlq.py
├── test_durable_wait_and_resume.py
├── test_remote_sandbox_job.py
├── test_marketplace_install_plugin.py
├── test_abac_denies_cross_project_artifact.py
├── test_data_deletion_request.py
├── test_siem_export.py
└── test_release_with_marketplace_package.py
```

## 26.3 E2E Tests

```text
tests/e2e/
├── test_tenant_onboarding_to_first_task.py
├── test_admin_installs_skill_from_marketplace.py
├── test_task_runs_in_remote_sandbox_with_quota.py
├── test_approval_notification_resume.py
├── test_billing_monthly_invoice.py
├── test_policy_simulation_and_enforcement.py
└── test_backup_restore_smoke.py
```

---

# 27. 三期开发顺序

## Sprint 1：Tenancy + Identity Hardening

交付：

```text
tenant/org/project/environment 模型
ResourceScope
TenantResolver
Repository tenant filter enforcement
RBAC role enhancement
API key/service account tenant binding
```

## Sprint 2：Quota + Billing Metering

交付：

```text
QuotaLimit / UsageRecord
QuotaEnforcer hooks
Usage metering
Billing ledger
Pricing plan
Usage export
```

## Sprint 3：Distributed Worker Queue

交付：

```text
Queue backend
Worker lease
Retry / DLQ
Worker heartbeat
Priority queue
Idempotency keys
```

## Sprint 4：Durable Execution

交付：

```text
DurableInstance
Checkpoint integration
Signal API
Timer wait
Human approval resume
Webhook resume
```

## Sprint 5：Remote Sandbox Cluster

交付：

```text
SandboxJob
Sandbox scheduler
Remote docker worker
Workspace sync
Artifact sync
Log streaming
Sandbox quota metering
```

## Sprint 6：Marketplace + Plugin Trust

交付：

```text
Marketplace package schema
Package registry
Signature/checksum verification
Install/uninstall
Permission review
Tenant-scoped install
```

## Sprint 7：Advanced Policy + Data Governance

交付：

```text
ABAC context
Policy simulation
Policy audit
Data classification
PII detection
Retention policy
Deletion request
```

## Sprint 8：Admin Console API + Web UI Skeleton

交付：

```text
Dashboard APIs
Task timeline API
Usage/Billing UI APIs
Marketplace UI APIs
Approval UI APIs
Frontend skeleton
```

## Sprint 9：Enterprise Integrations + Compliance

交付：

```text
OIDC SSO basic
SIEM export
Compliance report
Audit export
Secret manager providers
```

## Sprint 10：SRE / HA / DR

交付：

```text
Health/readiness
SLO definitions
Backup/restore
Capacity metrics
Runbooks
Helm chart
Production deployment docs
```

---

# 28. 三期 Definition of Done

三期完成标准：

```text
1. 平台支持 tenant / org / project / environment 资源隔离。
2. 所有核心资源查询强制 tenant scoped。
3. API Key 和 Service Account 支持租户绑定。
4. Quota 系统可限制 token、模型调用、工具调用、sandbox 时长、并发任务。
5. Billing 系统可生成 usage ledger 和月度 invoice 草稿。
6. Runtime 支持分布式 worker queue、lease、retry、DLQ。
7. 长期任务支持 durable wait/resume/signal。
8. Remote sandbox cluster 可执行隔离任务并回传 artifacts。
9. Marketplace 支持 package 发布、验证、安装、卸载。
10. 插件安装需经过权限声明、签名/校验和、risk review。
11. Web Admin Console 至少覆盖 dashboard、tasks、deployments、marketplace、usage、approvals。
12. Policy 支持 ABAC、policy simulation、policy audit。
13. Data Governance 支持分类、PII 检测、retention、deletion request。
14. 企业集成至少支持 OIDC SSO 基础版与 SIEM audit export。
15. Experiments 支持 guardrail metrics、kill switch、rollout。
16. SRE 支持 health/readiness、SLO、backup/restore、capacity metrics。
17. 所有三期新增能力均有 RuntimeEvent / AuditEvent。
18. 跨租户访问集成测试必须覆盖 memory、artifact、knowledge、task、event。
19. 关键三期模块单元测试覆盖率 >= 80%。
20. 三期 E2E 覆盖 tenant onboarding、quota block、billing invoice、marketplace install、remote sandbox、durable resume、backup restore。
```

---

# 29. 风险与应对

| 风险 | 说明 | 应对 |
|---|---|---|
| 多租户隔离遗漏 | 任一 repository 漏 tenant filter 都可能越权 | 强制 ResourceScope、repository base class、集成测试、静态扫描 |
| 计费错误 | 用量计量和账单错误影响商业化 | UsageRecord 不可变、ledger 幂等、账单可重算 |
| 分布式任务重复执行 | worker retry/lease 可能导致副作用重复 | idempotency key、tool executor 幂等、外部调用去重 |
| Remote sandbox 安全 | 远程执行风险高 | 默认无网络、短时凭证、隔离 workspace、审计、资源限制 |
| Marketplace 供应链风险 | 第三方插件可带恶意代码 | 签名、checksum、权限声明、沙箱、allowlist、trust level |
| ABAC 策略复杂 | 策略难以理解和调试 | simulation、matched rules、policy audit、deny overrides |
| Durable 版本兼容 | 长期任务恢复时 workflow/prompt/skill 已升级 | instance 绑定 release_id，version-safe resume |
| 数据删除与审计冲突 | 合规删除和审计不可变存在冲突 | payload 预脱敏、redaction overlay、保留审计元数据 |
| Admin Console 权限风险 | 管理端误操作影响大 | RBAC、二次确认、审计、rollback |
| SRE 成本 | HA/DR 增加复杂度 | 先做单 region HA，再预留 multi-region |

---

# 30. 三期与四期边界

三期完成后，平台具备企业级生产与商业化能力。

四期可能方向：

```text
跨区域 active-active
联邦多 Agent 网络
自优化 Agent 组织结构
自动 Prompt/Skill 进化
企业私有模型训练与微调平台
Agent 经济系统与结算网络
端到端合规认证自动化
行业模板市场
低代码 Agent Builder
```

这些不是三期交付目标。

---

## 31. 结论

三期的本质是将二期平台从“功能完整”推进到“企业级可运营”。

核心目标可以归纳为：

```text
1. 隔离：Tenant / Project / Resource Scope
2. 控制：Quota / Policy / Governance / Compliance
3. 商业：Billing / Usage / Marketplace
4. 规模：Distributed Runtime / Remote Sandbox / Durable Execution
5. 运维：SRE / HA / Backup / Restore
6. 管理：Web Console / Enterprise Integrations
```

三期完成后，Agent Platform 将具备：

```text
Multi-tenant
Quota-controlled
Billable
Marketplace-enabled
Remote-sandboxed
Durable
Distributed
Policy-governed
Compliance-ready
SRE-operable
Enterprise-integrated
```

这时平台已经不只是 Agent Framework，而是可以作为企业级 AI Agent 基础设施长期运营。

