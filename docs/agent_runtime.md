# Agent Runtime / Session / Pattern

本阶段一次实际执行统一建模为 `AgentRun`，执行关联字段使用 `agent_run_id`。`Task` 不表示 runtime 执行单元，保留给后续 planning/todo/reminder/Markdown plan engine。

## API

- `POST /api/v1/sessions`：创建 Session。
- `GET /api/v1/sessions/{session_id}`：读取 Session。
- `GET /api/v1/sessions/{session_id}/messages`：读取用户可见历史。
- `POST /api/v1/agent-runs`：创建并执行 AgentRun。
- `GET /api/v1/agent-runs/{agent_run_id}`：读取运行状态。
- `GET /api/v1/agent-runs/{agent_run_id}/events`：读取低频事实事件。
- `POST /api/v1/agent-runs/{agent_run_id}/cancel`：显式取消运行。

普通响应继续使用 `{"code": number, "msg": string, "data": object}`。当 `POST /agent-runs` 请求 `stream=true` 时返回 `text/event-stream`，事件包括：

- `run.started`
- `output.text.delta`
- `run.completed`
- `run.failed`
- `run.cancelled`

只有 pattern 标记为 `public_output` 的模型动作会映射为 `output.text.delta`。routing、ReAct 工具意图、reflection draft/critique 等内部阶段不会写入 SSE，也不会写入 Session。

## Runtime Flow

1. API 校验 Session、mode 和 requested pattern。
2. `PatternSelector` 按显式 pattern、mode 默认、`single_turn` fallback 选择策略。
3. `SessionManager` 追加 user message，并将该 sequence 固定为 `context_message_sequence`。
4. `AgentRunManager` 创建 run，保证同一 Session 只有一个 `created/running` run。
5. `AgentRuntimeKernel` 执行 pattern action loop。
6. Runtime 统一执行模型、mock tool、pattern transition、完成、失败和取消。
7. 成功完成时仅写入最终 assistant message。

## Patterns

内置 pattern：

- `single_turn`：一次公开模型响应后完成。
- `planning`：输出结构化计划文本，不创建 Task/todo/reminder/Markdown。
- `chaining`：默认两阶段，内部分析后公开最终答案。
- `routing`：规则优先，未命中时可用内部模型分类并转移目标 pattern。
- `react`：内部工具决策、mock tool observation、公开最终答案。
- `reflection`：内部 draft、内部 critique、公开 revise。

默认 mode 映射：

- `chat -> single_turn`
- `plan -> planning`
- `build -> react`
- `review -> reflection`

## Tool Boundary

当前仅提供无外部副作用的 mock executor：

- `mock.echo`
- `mock.lookup`

mock executor 不执行命令、不访问文件、不访问网络、不读取外部凭证。事件只记录工具名、call id、状态和安全分类，不记录完整参数或敏感 observation。

## SSE Disconnect And Cancel

`stream=true` 时，服务端检测到客户端断连后通过 cancellation token 将 run 视为 `cancelled`，并避免提交未完成 assistant message。显式 `POST /cancel` 使用同一取消语义，区别仅是 trigger 为 `explicit`。

当前实现是 service request 内同步执行，不提供断线续传、worker 接管或跨进程恢复。

## Events

数据库相关代码集中在 `src/storage/database/`：

- `session.py`：SQLAlchemy async engine/session 依赖。
- `base.py` / `orm_types.py`：ORM base、UUID/timestamp mixin 和 enum 类型。
- `models/`：`sessions`、`agent_runs`、`runtime_events` 等 ORM records。
- `repositories/`：Session、AgentRun、RuntimeEvent 的持久化访问。

`runtime_events` 按 `agent_run_id` 和 sequence 记录低频事实：

- run started/completed/failed/cancelled
- pattern selected/transitioned
- step started/completed
- model invocation started/completed/failed/tool calls produced
- tool action executed

事件 payload 不保存完整 prompt、raw provider body、逐 token delta 或完整工具参数。

## Migration / Rollback

Alembic migration 创建：

- `sessions`
- `session_messages`
- `agent_runs`
- `agent_run_steps`
- `runtime_events`

并包含 session 活动 run partial unique index、message/event/step sequence 唯一约束和 downgrade 删除路径。

回滚顺序：

1. 下线 `/api/v1/sessions` 与 `/api/v1/agent-runs` 写入入口。
2. 执行 Alembic downgrade 删除新增表与索引。
3. 移除 runtime/session/pattern/tool 代码。

本阶段不迁移既有 Task 数据，也不提供 `/tasks` 兼容执行入口。
