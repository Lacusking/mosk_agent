# Agent Platform 项目说明（PRD/LLD 基线）

## 1. 文档目的

本文件是 OpenSpec 变更的项目基线说明，唯一目标是约束后续 proposal/spec/design/tasks 的方向一致性。

约束来源：
- 产品需求文档：`docs/agent_platform_prd.md`
- 低层设计文档：`docs/agent_platform_lld.md`

若后续实现或方案与本文件冲突，以 PRD/LLD 的明确版本决策为准，并在变更中说明原因。

## 2. 项目定位

Agent Platform 是一个 **Python 实现的通用 Agent Runtime 与治理平台**，不是单一场景应用。

平台定位关键词：
- Pattern-driven
- Runtime-driven
- Multi-Agent
- Tool-Governed
- Memory-Aware

平台目标：在统一运行时内，完成从请求接入到任务交付的全链路闭环，并保证可治理、可观测、可回放、可评估。

## 3. 平台形态（长期）

按照 PRD，平台最终形态包含：
- Python SDK
- Runtime Service
- API Server
- CLI
- Worker Pool
- Control Plane
- Observability & Evaluation Console

说明：以上为长期形态，不代表全部进入 MVP。

## 4. MVP 决策基线（当前开发级别）

以下为 LLD 明确的 MVP 边界，属于强约束：

- 交互形态：`API + CLI` 首发，不做 Web UI
- 模型接入：`OpenAI + Mock`
- Memory：仅 `Summary Memory`
- Sandbox：开发环境 `subprocess runner`
- 租户模式：单租户（default tenant）
- MCP：第一版支持
- A2A：第一版支持基础能力
- Deployment：Prompt/Skill/Policy 版本发布纳入第一版
- Eval：保留扩展接口，但不是 MVP 阻塞项

## 5. 非目标（当前阶段）

以下能力当前不作为 MVP 交付目标：
- 完整 Knowledge/RAG 能力
- 生产级容器隔离（Docker/Firecracker）
- 多租户强隔离
- Web Console
- 复杂工作流补偿机制
- Semantic/Entity/Episodic Memory
- 将 Evaluation 作为发布阻塞条件

## 6. 核心执行闭环

OpenSpec 设计必须围绕如下主链路展开：

`Request -> Access -> Identity -> Session Bind -> Runtime Create AgentRun -> Pattern Select/Execute -> Context Assemble -> Prompt Render -> Model Invoke -> Tool/MCP/A2A Dispatch -> Observation Append -> Summary Memory Update -> Artifact Persist -> Event Store -> Final Response`

任何新能力必须明确：
- 在主链路中的位置
- 对上下游模块的输入输出影响
- 失败时回退与可观测行为

## 7. 分层架构约束

MVP 方案应遵循以下分层：
- 接入与身份层：`access, identity, api, cli`
- 运行时核心层：`runtime, events, agent_runs, sessions, scheduler, workers`
- 智能编排层：`models, prompts, skills, hooks, patterns, workflow`
- Agent 层：`agents, multi_agent`
- 工具与执行层：`tools, connectors, sandbox`
- 上下文与记忆层：`context, memory, knowledge, rag`
- 数据与产物层：`vfs, artifacts, storage`
- 治理与可观测层：`policy, governance, observability, evaluation, experiments, notifications`
- 公共契约层：`core, contracts`

跨模块数据交互必须通过 `contracts/` 中的 schema 协议，不允许隐式结构。

## 8. 开发级别约束（P0/P1/P2）

### 8.1 P0（MVP 必做）

- `access`：请求归一化、AccessContext
- `identity`：单租户、API Key、本地用户上下文
- `api`：FastAPI 核心会话与 AgentRun 接口
- `cli`：Typer 本地运行与调试入口
- `runtime`：AgentRun 状态机、事件循环、step runner
- `events`：Event Sourcing、Event Store
- `agent_runs`：AgentRun/AgentRunStep 与状态持久化
- `sessions`：会话历史与 summary compaction
- `models`：OpenAI + Mock Adapter
- `prompts`：模板加载、渲染、格式化、版本基础能力
- `skills`：Manifest/Registry/Loader/Resolver
- `hooks`：基础 Hook 生命周期
- `patterns`：single_turn/chaining/routing/planning/react/reflection 模式及选择器；planning 不等同 Task 持久化
- `agents`：BaseAgent/GeneralAgent/Supervisor 基础版
- `tools`：Registry/Router/Executor/MCP Adapter
- `context`：上下文组装与 token budget
- `memory`：Summary Memory
- `vfs`：workspace/artifacts/memories 路径边界
- `sandbox`：subprocess runner（开发期）
- `policy`：Tool/Skill/Prompt 基础策略
- `governance`：audit、risk guard、approval stub
- `observability`：trace_id、日志、token/cost 基础统计
- `deployment`：Prompt/Skill/Policy version binding
- `storage`：SQLite/PostgreSQL repository

### 8.2 P1（增强能力，非阻塞）

- `tasks`：后续计划/待办执行引擎；不作为 Agent runtime 执行单元
- `workflow`：linear / DAG 基础 runner
- `multi_agent`：subagent 与 A2A 深化
- `connectors`：HTTP/filesystem/MCP connector 扩展
- `artifacts`：metadata 管理增强
- `workers`：async worker 基础能力
- `scheduler`：后台调度接口与基础实现
- `notifications`：Webhook 通知 stub
- `control_plane`：Prompt/Skill/Policy 管理 API 基础版
- `plugins`：插件 manifest 与本地 loader

### 8.3 P2（预留接口）

- `knowledge`：知识资产管理完整能力
- `rag`：检索增强完整能力
- `evaluation`：完整评测体系
- `experiments`：实验与灰度能力

### 8.4 分级执行规则

- 不得将 P1/P2 能力作为 P0 设计前提或交付阻塞条件。
- P0 方案优先复用现有模块，禁止为未来场景提前引入复杂抽象。
- 若确需新增抽象，必须在 design 中说明其对当前 P0 问题的直接价值。

## 9. 接口与契约约束

- API 风格：REST
- API 版本：`/api/v1`
- 默认响应结构：
  - `code`（数字）
  - `msg`（字符串）
  - `data`（对象）
- API 必须可生成 OpenAPI 文档
- 关键跨模块 schema（如 AgentRequest、AgentRun、RuntimeEvent、ToolDefinition）优先定义在 `contracts/`

## 10. 安全、治理与审计约束

所有高风险动作（工具调用、命令执行、文件访问、外部连接、记忆写入）必须满足：
- 可策略判定（Policy）
- 可风险分级（Risk）
- 可审批拦截（Approval，可为 stub）
- 可审计追踪（Audit + RuntimeEvent）

设计中必须显式声明权限边界、路径边界、失败分支和降级策略。

## 11. 可观测与回放约束

- Runtime 关键节点必须产生日志/事件：AgentRun、Model、Tool、Memory、Artifact。
- 事件存储是回放与排障事实来源，不可跳过。
- 成本与 Token 使用量必须可统计。
- 观测组件失败不应阻断主链路（除非需求显式要求阻断）。

## 12. OpenSpec 编写约束（执行层）

后续所有 OpenSpec 变更（proposal/spec/design/tasks）需遵循：
- 与第 4 节 MVP 边界保持一致
- 与第 8 节开发级别一致（标明 P0/P1/P2）
- 明确受影响模块（src/<模块名>/testing/database/devops/docs）
- 若涉及数据库变更，必须包含 migration 与回滚策略
- 每个任务必须给出可执行验证方式（命令或手工路径）
- 不允许“顺手重构”无关模块

## 13. 术语

- Agent：执行请求的智能体实例
- AgentRun：一次 API/CLI 请求触发的 Agent 执行生命周期单元，使用 `agent_run_id` 关联事件、步骤和模型调用
- AgentRunStep：AgentRun 内部执行步骤（pattern/model/tool/agent/workflow/human/system）
- Task：未来由 planning 能力驱动的计划/待办记录与提醒对象，不是 Agent runtime 执行单元；当前 AgentRun/Session/Pattern 变更不实现其持久化行为
- Skill：可复用能力包（Prompt + Tool Scope + Policy + Hooks + Memory Scope）
- Prompt Pack：可版本化的提示模板资产
- Tool：被模型/运行时调用的外部能力
- A2A：Agent-to-Agent 协议交互
- MCP：Model Context Protocol 资源与工具交互
- Summary Memory：会话摘要记忆
- Artifact：任务产出物（文档、报告、代码、图表等）
