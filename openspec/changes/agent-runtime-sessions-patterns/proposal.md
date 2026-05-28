## Why

当前仓库已有模型协议、统一模型事件与 adapter 基座，但尚无会话历史、一次 Agent 执行的生命周期资源、策略编排层或对客户端的运行级流输出。因而 service API 不能执行并追踪一个完整的 agent loop，也无法验证 ReAct 的模型调用、动作执行、观察回流闭环。

本变更明确一次实际执行为 `AgentRun`；`Task` 留给后续 planning 联动、todo/reminder 或持久化计划能力，避免将运行状态和计划语义混在同一资源中。

## What Changes

- 新增 Session 与可见消息历史能力，按 `context_message_sequence` 固定每次运行读取的上下文水位。
- 新增 AgentRun/step 生命周期、事实事件、取消处理和 `POST /api/v1/agent-runs` 的同步或 SSE 流式执行路径。
- 新增 pattern registry/selector，并提供 `single_turn`、`chaining`、`routing`、`planning`、`react`、`reflection` 六种最小可执行策略；mode 只决定默认策略，显式 pattern 可覆盖。
- 新增最小 `ToolActionExecutor` port 与无外部副作用的 mock executor，使 ReAct 可通过集成测试闭环验证。
- 为 `BaseError` 增加 `http_status` 属性，使 API 异常能正确区分 401/404/409/422 等 HTTP 状态码。
- **BREAKING**：现有运行事件/model metadata 中代表执行关联的字段从 `task_id` 统一修订为 `agent_run_id`；未来 Task 不作为本次运行资源实现。

## Capabilities

### New Capabilities
- `session-conversation-history`：持久化 Session、用户可见消息历史与运行上下文水位。
- `agent-run-runtime`：管理 AgentRun 生命周期、步骤、事实事件、取消与同步/SSE 输出。
- `agent-pattern-orchestration`：注册、选择并执行六类可组合 Agent 策略。
- `minimal-tool-action-port`：提供 ReAct 测试可用的类型化动作端口与无副作用 mock executor。

### Modified Capabilities
- 无。本变更依赖进行中的 `model-protocol-adapters-and-event-contracts` change 完成 `model-runtime-event-contracts` 中执行关联字段到 `agent_run_id` 的修订。

## Impact

- 受影响模块：`src/contracts`、`src/sessions`、`src/agent_runs`、`src/runtime`、`src/patterns`、`src/tools`、`src/events`、`src/api`、`tests`、`database`、`docs`。
- API 兼容性：新增 `/api/v1/sessions` 与 `/api/v1/agent-runs` 路由及 SSE envelope；`task_id -> agent_run_id` 为执行事件契约的非兼容命名修订。当前尚无稳定公开 AgentRun API，因此在首轮落地前完成修订成本最低。
- 配置风险：新增默认 mode/pattern、最大 step、timeout、模型重试额度和仅供 dev/test 的 mock tool 开关；错误开启 mock 工具会造成能力暴露误解，生产配置必须默认关闭或拒绝 ReAct 工具动作。
- 数据迁移风险：新增 `sessions`、`session_messages`、`agent_runs`、`agent_run_steps`、`runtime_events` 五表及活动 run 唯一约束；需要 Alembic upgrade/downgrade 验证，不迁移既有 Task 数据。
- 关键假设与取舍：当前 API 请求内同步驱动 run；一个 session 同时最多一个活动 run；历史只提交用户输入与成功完成的 assistant 输出；planning 不创建 Task/todo/Markdown；ReAct 当前仅执行 mock tool。该路径复用既有 ModelAdapter 和事件契约，不提前实现真实工具、memory、policy 或 worker。

## Non-goals

- 不实现 Task 引擎、todo/reminder、Markdown plan、memory/context compaction、policy/hooks/approval。
- 不实现真实工具、外部副作用、MCP/A2A 调度、多 Agent、异步 worker、流断线续传或跨进程恢复。
