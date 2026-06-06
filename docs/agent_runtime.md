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
5. `ContextBuilder` 读取水位内最近 session messages，合并当前 run 已完成的工具 observation，构造 `ContextBundle`，并通过 context strategy pipeline 做裁剪与预算控制。
6. `AgentRuntimeKernel` 在每轮 pattern 决策前重新构造上下文，将 `ContextBundle.to_model_messages()` 放入 `PatternRuntimeState.visible_context_messages`，再执行 pattern action loop。
7. Runtime 统一执行模型、mock tool、pattern transition、完成、失败和取消。
8. 成功完成时仅写入最终 assistant message。

## Context Assembly

上下文装配入口位于 `src/context`：

- `ContextItem`：包装单段上下文，记录 source/type/content/priority/token_count/pinned/evictable/metadata。
- `ContextBundle`：按 AgentRun 聚合 session messages、memory summary、tool observations、artifacts，并记录被裁剪的 evicted items 与预算诊断。
- `TokenCounter`：提供默认字符估算器 `DefaultTokenCounter`，可选使用已安装的 `TiktokenCounter`；builder 使用 token_count 做预飞行预算校验。
- `ContextBuilder`：按 `context_message_sequence` 和 `CONTEXT_WINDOW_MESSAGES` 读取最近消息，提取当前 run 已完成且未失败的 `tool_result` observation，并按 call_id 去重。
- `ContextStrategyPipeline`：默认顺序执行 `SnipCompactStrategy`、`MicroCompactStrategy`、`ToolResultBudgetStrategy`；`AutoCompactStrategy` 可注入 summarizer 但默认关闭，`ReactiveCompactStrategy` 保留给后续独立策略化。

预算配置位于 `AgentRuntimeConfig`：

- `CONTEXT_TOKEN_BUDGET`：profile 未声明 context window 时的全局默认上限。
- `CONTEXT_TOKEN_RESERVE`：从输入上下文预算中扣除的输出预留空间。
- `CONTEXT_MICRO_ITEM_MAX_TOKENS`：单个 ContextItem 的 microCompact 上限。
- `CONTEXT_TOOL_RESULT_BUDGET_TOKENS`：tool observations 的总 token 上限。

ReAct 当前 run 内的模型响应和工具结果仍由 `PatternRuntimeState.observations` 管理，用于 pattern 动作决策；`ContextBundle.tool_observations` 只是模型可见上下文的一部分。pattern 不直接访问 ContextBundle。builder 只装配成功完成的 tool result，失败或进行中的 observation 留在 `PatternRuntimeState.observations`。

当 provider 返回 `context_length_exceeded` 时，错误映射器生成 `ModelContextLengthError`。runtime 的 `decide_model_error()` 会在未发送公开 delta 且该 step 尚未缩减重试时返回 `context_reduction_retry`，kernel 以更少尾部消息和 micro 截断后的 request 重试一次；第二次仍超限则按模型错误失败 run，避免无限循环。

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

## Model Runtime Target

runtime 通过 `src/runtime/factory.py` 构造模型调用目标。默认保持本地 mock，避免开发环境必须配置外部凭证：

- `RUNTIME_MODEL_PROVIDER=mock`
- `RUNTIME_MODEL_NAME=mock-model`
- `RUNTIME_MODEL_PROTOCOL=mock`

切换到 OpenAI 时使用同一工厂注册 OpenAI provider、profile 和 protocol adapter：

- `RUNTIME_MODEL_PROVIDER=openai`
- `RUNTIME_MODEL_NAME=<OpenAI model name>`
- `RUNTIME_MODEL_PROTOCOL=openai_responses` 或 `openai_chat`
- `OPENAI_API_KEY=<key>`
- `OPENAI_BASE_URL=https://api.openai.com/v1`
- `OPENAI_TIMEOUT_SECONDS=30`
- `RUNTIME_MODEL_CONTEXT_WINDOW_TOKENS=<optional context window>`

`AgentRuntimeKernel` 的 request provider/model/protocol 与 factory 构造出的 `RuntimeModelTarget` 保持一致；OpenAI 缺少 API key 时在工厂阶段失败，不会落到 transport 层才暴露配置错误。

`POST /api/v1/agent-runs` 也可以为单次 run 覆盖模型选择；未提供字段时使用上述配置默认值：

```json
{
  "session_id": "...",
  "input": "hello",
  "model_provider": "openai",
  "model_name": "gpt-4.1-mini",
  "model_protocol": "openai_responses",
  "model_context_window_tokens": 128000
}
```

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
