## Context

`model-protocol-adapters-and-event-contracts` 已提供 `ModelRequest`、`ModelResponse`、`ModelStreamEvent`、标准模型错误与模型生命周期事件定义。仓库中的 `src/runtime`、`src/sessions`、`src/patterns` 和 `src/tools` 仍为空骨架，API 目前仅暴露 health endpoint，存储基础采用 PostgreSQL、SQLAlchemy async session 与 Alembic。

本变更基于已确认的术语修订：一次实际执行是 `AgentRun`，以 `agent_run_id` 贯穿 step、event 与 model metadata；`Task` 仅保留为未来 planning/todo/reminder/Markdown plan 引擎的概念。当前 service API 每次请求触发一个 run，不引入 session loop 与 run loop 的双层调度。

## Goals / Non-Goals

**Goals:**

- 持久化 Session 与可见消息历史，为每个 AgentRun 固定上下文水位。
- 建立 AgentRun 生命周期、step runner、事实事件存储、取消与 SSE 输出。
- 以可插拔动作契约完整支持 `single_turn`、`chaining`、`routing`、`planning`、`react` 与 `reflection`。
- 为 ReAct 提供无外部副作用的最小 tool action port 与 mock executor，完成端到端测试。
- 复用现有 models contracts、ModelAdapter、stream reducer 与 ModelError，不解析 provider 私有响应。

**Non-Goals:**

- 不实现 Task/todo/reminder/Markdown plan、summary compaction 或 memory 写入。
- 不实现真实工具、MCP/A2A dispatch、policy/hooks/approval、sandbox、artifact 或 multi-agent 执行。
- 不引入 worker、持久化 SSE delta、断线续传或跨进程 run 接管。
- 不实现自动 provider fallback、成本定价或生产级重试调度。

## Architecture

### 执行关系

```text
POST /api/v1/sessions
          |
          v
POST /api/v1/agent-runs (session_id, input, mode, requested_pattern?, stream)
          |
          v
+------------------- AgentRuntimeKernel -------------------+
| SessionManager: append user message + context watermark   |
| AgentRunManager: create/run/finalize/cancel               |
| PatternSelector -> Pattern.next_action()                  |
|        |                                                  |
|        +-> InvokeModelAction -> existing ModelAdapter     |
|        |          | -> ModelStreamEvent -> public SSE     |
|        |          + -> ModelResponse observation          |
|        +-> InvokeToolAction -> MockToolActionExecutor     |
|        +-> TransitionPatternAction                        |
|        +-> CompleteAction / FailAction                    |
| EventStore: durable low-frequency facts                   |
+-----------------------------------------------------------+
          |
          v
SessionManager: commit final assistant message only on completion
```

### 所有权与集成边界

| 模块 | 本变更所有权 | 复用/不承担 |
|---|---|---|
| `src/contracts` | Session、AgentRun、PatternAction、ToolAction、API stream payload；扩展 event 类型 | 不含 ORM 查询逻辑 |
| `src/sessions` | 会话创建、消息顺序、history watermark、最终消息提交 | 不压缩 summary，不运行模型 |
| `src/agent_runs` | AgentRun/step 业务 manager 与状态编排 | 不决定 pattern 算法，不承载 ORM/repository 实现 |
| `src/runtime` | kernel、动作执行、stream 映射、错误策略、取消、事件构造 | 不解析 provider wire body |
| `src/patterns` | registry、selector、mode 映射和六类策略状态 | 不写 Session/EventStore，不直接执行 IO |
| `src/tools` | `ToolActionExecutor` port 与 mock 实现 | 不是真实工具 registry/治理系统 |
| `src/events` | RuntimeEvent 类型与服务发现入口 | 不持久化逐 token delta，不承载 repository 实现 |
| `src/storage/database` | SQLAlchemy session、ORM base/types、ORM records、Session/AgentRun/RuntimeEvent repositories | 不放业务编排逻辑 |
| `src/models` | 既有 ModelAdapter 和流归约输入 | 仅按前置 change 修订 `agent_run_id` metadata |
| `src/api` | 认证后的 REST/SSE 适配 | 不包含运行编排逻辑 |

### 生命周期状态机

```text
created -> running -> completed
              |  \
              |   -> failed
              -> cancelled
```

`planning`、`routing`、`react` 与 `reflection` 是执行策略，不是 run 状态。其选择与转移记录为 `AgentRunStep` 和 `RuntimeEvent`。工具等待或人工恢复状态留待真实工具/审批能力引入时补充。

### Pattern Action 协议

Pattern 使用同一内部状态输入并只输出下一动作：

```text
PatternRuntimeState
  agent_run
  visible_context_messages
  observations
  step_count

NextAction
  InvokeModelAction(messages/options/tools/output_visibility)
  InvokeToolAction(tool_call)
  TransitionPatternAction(target_pattern)
  CompleteAction(final_content)
  FailAction(reason)
```

Runtime 为每个动作创建 step，执行后将 observation 反馈给同一 pattern 或转移后的 pattern。该边界使流输出、取消、重试和事件持久化只有一份实现。

`output_visibility` 仅取 `internal` 或 `public_output`。多阶段 pattern 的 routing 判定、工具意图、draft 与 critique 必须标记为 `internal`，其模型 delta 不向客户端输出也不写入 Session；只有已进入用户最终答案阶段的 action 可标记为 `public_output` 并映射为 `output.text.delta`。例如 reflection 仅 revised final 阶段公开，ReAct 在工具观察完成后通过公开 final-generation action 流出最终答案。

## Components

### Sessions

- `contracts/sessions.py` 定义 `SessionStatus`、`Session`、`SessionMessage` 与 API schemas。
- `storage/database/repositories/sessions.py` 负责 Session CRUD、按 sequence 读取/追加消息及活动 run 关联检查。
- `sessions/manager.py` 在创建 run 时原子追加 user message 并得到 `context_message_sequence`；仅在 run 成功完成后追加 assistant 消息。
- 首期消息内容复用稳定的模型 content blocks 表达文本；内部 critique、route 与 tool observation 不进入历史。

### Agent Runs 与 Runtime

- `contracts/agent_runs.py` 定义 `AgentRunStatus`、`AgentRun`、`AgentRunStep`、finish/error 信息与 API schema。
- `storage/database/repositories/agent_runs.py` 持久化 run/step，使用条件更新保障终态不可反转。
- `runtime/kernel.py` 驱动动作循环；`runtime/state_machine.py` 校验状态转换；`runtime/error_policy.py` 消费 `ModelError`；`runtime/stream.py` 映射 SSE；`runtime/cancellation.py` 提供进程内取消令牌及持久化状态判断。
- `storage/database/repositories/events.py` 持久化 RuntimeEvent；现有模型事件 envelope 在前置变更中将 `task_id` 更名为 `agent_run_id`，本变更新增 run/pattern/tool payload。

### Patterns

```text
patterns/
├── base.py                 # Pattern / NextAction / PatternRuntimeState
├── registry.py             # registered implementation lookup
├── selector.py             # explicit > mode default > single_turn fallback
├── modes.py                # chat/plan/build/review 默认映射
├── single_turn/pattern.py
├── chaining/pattern.py
├── routing/pattern.py
├── planning/pattern.py
├── react/pattern.py
└── reflection/pattern.py
```

| Pattern | 最小可执行行为 |
|---|---|
| `single_turn` | 一次模型响应后完成 |
| `chaining` | 按 `ChainConfig` 定义的有序阶段序列执行，每阶段产出传入下一阶段 |
| `routing` | 配置规则优先；规则未命中时以受控模型分类决策产生 `TransitionPatternAction` |
| `planning` | 以规划专用 system prompt 引导模型输出结构化计划文本，作为 assistant 消息完成 |
| `react` | internal tool decision -> validated mock action -> observation -> public final generation，受 max steps 限制 |
| `reflection` | internal draft -> internal critique -> public revised final 三阶段执行 |

默认 mode 映射为：`chat -> single_turn`、`plan -> planning`、`build -> react`、`review -> reflection`。显式请求覆盖默认映射；selector 仅选择注册且当前能力满足的 pattern。

#### Chaining 阶段配置

Chaining 通过 `ChainConfig` 定义有序阶段序列。每个阶段是一次独立的 `InvokeModelAction`，可附带阶段专属 system prompt 和 output visibility：

```text
ChainConfig
  stages: list[ChainStage]       # 至少 2 个阶段，最后一个必须为 public_output

ChainStage
  name                            # 阶段标识，用于 step/event 记录
  system_prompt?                  # 该阶段追加的系统指令
  output_visibility               # internal | public_output
  inject_previous_output: bool    # 是否将前序阶段的模型输出注入本阶段 user context
```

执行流程：stage[0] 产出 -> 若 `inject_previous_output`，作为额外 user message 注入 stage[1] context -> ... -> 最后一个 stage 标记 `public_output` 并形成最终响应。中间阶段 `internal` 输出不写 Session 也不流 SSE。

`ChainConfig` 首期以代码注册方式提供（在 `patterns/chaining/pattern.py` 中声明），不通过 API 请求动态传入。后续可扩展为配置文件或 Skill 绑定。若 `stages` 为空或只有一个阶段，selector 拒绝该 pattern 并报 `ValidationError`。

#### Routing 决策机制

Routing 采用两层决策：先执行配置规则匹配，未命中时 fallback 到受控模型分类。

```text
RoutingConfig
  rules: list[RoutingRule]         # 按序评估，首条命中即转移
  model_fallback: bool             # 规则全部未命中时是否使用模型分类；默认 true
  allowed_targets: list[str]       # 模型分类时允许选择的目标 pattern 集合

RoutingRule
  condition_type: keyword | regex  # 输入文本匹配方式
  condition_value: str             # 匹配模式
  target_pattern: str              # 命中后转移的目标 pattern
```

执行流程：
1. 按顺序对 user input 评估 `rules`；首条匹配的 rule 直接产生 `TransitionPatternAction(target_pattern)`。
2. 若无 rule 命中且 `model_fallback=true`：以 `internal` 可见性发起一次模型调用，system prompt 约束模型只能从 `allowed_targets` 中输出一个 pattern 名称；模型返回的文本经过严格校验后产生 `TransitionPatternAction`。
3. 若模型返回的 pattern 名称不在 `allowed_targets` 或未注册，routing 以 `FailAction` 终止 run。
4. 若无 rule 命中且 `model_fallback=false`：fallback 到 `single_turn`。

routing 本身的模型调用步骤标记为 `internal`，不产生用户可见输出。`RoutingConfig` 首期以代码注册方式提供。

#### Planning 输出行为

Planning 不创建 Task/todo/reminder/Markdown plan，也不动态产生 chaining 或其他 pattern 的执行链。它的最小可执行行为是：

1. 以规划专用 system prompt（引导模型按步骤或结构化格式输出计划）发起一次 `public_output` 的 `InvokeModelAction`。
2. 模型返回的计划文本作为最终 assistant 消息写入 Session 并通过 SSE 流出。
3. Pattern 产生 `CompleteAction`。

Planning 与 `single_turn` 的核心区别在于：planning 模式下 system prompt 明确引导模型输出结构化规划（而非直接回答问题），且 mode 映射使客户端可以按意图选择。后续 Task Engine 变更可扩展 planning 使其能将计划步骤物化为可执行 Task，但本次 planning 只产生文本输出。

### Minimal Tool Action

- `contracts/tools.py` 仅增加 `ToolActionRequest`、`ToolActionResult`、工具错误与安全审计 payload。
- `tools/base.py` 定义 `ToolActionExecutor` port；`tools/mock.py` 提供确定性 `mock.echo` 与 `mock.lookup` 等无副作用 executor。
- runtime 仅可把 models 层已完成校验的 `ModelToolCall` 转为 action；mock executor 仍校验注册名称与 arguments schema。
- mock tool 不执行命令、不读取文件、不调用网络，也不表示 MVP 完整 tools 模块已经实现。

## APIs

所有 REST 请求使用 `Authorization: Bearer <api-key>`，错误继续使用 `{code,msg,data}` 结构。SSE response 因传输语义使用 event data envelope，不包裹普通 JSON response。

| Method | Path | 作用 | 关键字段 |
|---|---|---|---|
| `POST` | `/api/v1/sessions` | 创建会话 | response: `session_id,status` |
| `GET` | `/api/v1/sessions/{session_id}` | 读取会话 | response: session metadata |
| `GET` | `/api/v1/sessions/{session_id}/messages` | 读取可见历史 | response: `messages[].sequence/role/content/agent_run_id` |
| `POST` | `/api/v1/agent-runs` | 创建并同步执行 run | request: `session_id,input,mode,requested_pattern?,stream` |
| `GET` | `/api/v1/agent-runs/{agent_run_id}` | 读取状态 | response: status/pattern/finish/error |
| `GET` | `/api/v1/agent-runs/{agent_run_id}/events` | 查询事实时间线 | response: typed runtime events |
| `POST` | `/api/v1/agent-runs/{agent_run_id}/cancel` | 显式取消 | response: cancelled state |

关键失败响应采用 HTTP 状态与稳定业务 `code`：无效或缺失 API key 返回 `401 / UNAUTHORIZED`，无效输入或不可用 mode/pattern 返回 `422 / VALIDATION_ERROR`，不存在的 session/run 返回 `404 / NOT_FOUND`，同 session 活动 run 冲突返回 `409 / AGENT_RUN_CONFLICT`。SSE 已建立后的执行失败不改写 HTTP 状态，而以 `run.failed` terminal event 携带安全错误分类。

当 `POST /api/v1/agent-runs` 的 `stream=false` 时，请求在当前 service 调用内运行到终态并返回普通响应。当 `stream=true` 时，同一个 POST 返回 SSE：

```text
event: run.started
data:  {agent_run_id, session_id, mode, pattern, trace_id}

event: output.text.delta
data:  {agent_run_id, sequence, delta}

event: run.completed | run.failed | run.cancelled
data:  {agent_run_id, status, finish_reason?, error_type?}
```

`output.text.delta` 只承载标记为 `public_output` 的最终回答阶段输出，不暴露 route、draft、critique、tool arguments 或 observation，且不写入 `runtime_events`；最终成功内容写入 `session_messages`。取消 endpoint 主要供另一个请求终止正在流出的 run。

## Data Model

所有新表以应用层 UUID V7 作为主键，并包含 `created_at`、`updated_at`。使用现有 PostgreSQL/SQLAlchemy/Alembic 基础，不增加存储后端。

### `sessions`

| 字段 | 说明 |
|---|---|
| `id` PK | session UUID V7 |
| `status` | `active` / `archived` |
| `title`, `metadata` | 可选显示与安全元数据 |
| `last_message_sequence` | 单调消息序号分配点 |
| `created_at`, `updated_at` | 审计时间 |

索引：`(status, updated_at)` 支持近期会话查询。

### `session_messages`

| 字段 | 说明 |
|---|---|
| `id` PK, `session_id` FK | 消息及所属会话 |
| `agent_run_id` FK nullable | 产生/消费该消息的 run |
| `sequence` | 会话内有序序号 |
| `role`, `content` JSONB, `metadata` JSONB | 可见消息内容 |
| `created_at`, `updated_at` | 审计时间；首期消息不可变 |

约束/索引：`UNIQUE(session_id, sequence)`；`(session_id, sequence)` 用于 history 读取。

### `agent_runs`

| 字段 | 说明 |
|---|---|
| `id` PK, `session_id` FK | `agent_run_id` 与所属会话 |
| `input_message_id` FK | 启动运行的 user message |
| `status`, `mode` | 生命周期状态和用户模式 |
| `requested_pattern`, `active_pattern` | pattern 请求与运行快照 |
| `context_message_sequence` | 输入上下文水位 |
| `trace_id`, `finish_reason`, `error_type` | 可观测终态 |
| `max_steps`, `timeout_seconds`, `retry_limit` | 执行限制 |
| `created_at`, `updated_at`, `started_at`, `completed_at` | 时间信息 |

索引：`(session_id, status)` 用于活动 run 检查；PostgreSQL partial unique index 对 `status IN ('created','running')` 的 `session_id` 保证首期串行执行；`trace_id` 索引支持诊断。

### `agent_run_steps`

| 字段 | 说明 |
|---|---|
| `id` PK, `agent_run_id` FK | step identity |
| `sequence`, `kind`, `status` | 运行内顺序和类型 |
| `pattern`, `invocation_id` | 策略/模型调用关联 |
| `safe_input`, `safe_output`, `error_type` | 经清洗的诊断信息 |
| `created_at`, `updated_at`, `completed_at` | 时间信息 |

约束/索引：`UNIQUE(agent_run_id, sequence)`；`(agent_run_id, sequence)` 支持 timeline。

### `runtime_events`

| 字段 | 说明 |
|---|---|
| `id` PK, `agent_run_id` FK, `step_id` FK nullable, `session_id` FK nullable | 关联标识 |
| `event_type`, `event_version`, `sequence` | 类型、版本、run 内排序 |
| `trace_id`, `span_id`, `parent_span_id` | trace |
| `actor_type`, `actor_id`, `payload` JSONB | 安全事实 |
| `created_at`, `updated_at` | 审计时间；event 追加后不可变 |

约束/索引：`UNIQUE(agent_run_id, sequence)`；`(agent_run_id, sequence)` 供事件查询；`trace_id` 供诊断。payload 不保存完整文本 delta、raw provider body 或完整工具 arguments。

### 本变更新增的 RuntimeEvent 类型与 Payload

前置 model change 已定义 `ModelInvocationStarted`/`Completed`/`Failed`/`ToolCallsProduced` 四类模型事件。本变更新增以下 run、pattern 与 tool action 事实事件：

| 事件类型 | Payload 核心字段 | 触发时机 |
|---|---|---|
| `AgentRunStarted` | `agent_run_id`、`session_id`、`mode`、`pattern`、`context_message_sequence`、`trace_id` | run 创建并开始执行 |
| `AgentRunCompleted` | `agent_run_id`、`status=completed`、`finish_reason`、`step_count`、`latency_ms` | run 成功完成 |
| `AgentRunFailed` | `agent_run_id`、`status=failed`、`error_type`、`error_classification`、`last_step_sequence`、`latency_ms` | run 因错误终止 |
| `AgentRunCancelled` | `agent_run_id`、`status=cancelled`、`trigger`（`explicit` / `sse_disconnect`）、`last_step_sequence`、`latency_ms` | run 被取消 |
| `PatternSelected` | `agent_run_id`、`pattern`、`selection_source`（`explicit` / `mode_default` / `fallback`）、`mode` | selector 确定执行策略 |
| `PatternTransitioned` | `agent_run_id`、`from_pattern`、`to_pattern`、`step_sequence`、`reason` | routing 或其他策略触发 pattern 切换 |
| `StepStarted` | `agent_run_id`、`step_id`、`sequence`、`kind`（`model` / `tool` / `transition` / `complete` / `fail`）、`pattern` | runtime 开始执行一个 step |
| `StepCompleted` | `agent_run_id`、`step_id`、`sequence`、`kind`、`status`（`succeeded` / `failed`）、`latency_ms` | step 执行结束 |
| `ToolActionExecuted` | `agent_run_id`、`step_id`、`tool_name`、`call_id`、`status`（`success` / `validation_failed` / `execution_failed`）、`latency_ms` | mock tool action 完成（成功或失败） |

所有 payload 遵循前置 change 的 `RuntimeEvent[Payload]` envelope 结构。Payload 不保存完整 prompt、完整工具参数值或 raw model body。`ToolActionExecuted` 仅记录工具名称、call id 与结果状态，不记录参数内容或 observation 全文。

## Decisions

### 1. AgentRun 替代执行型 Task

运行 API、状态机、event 和 model metadata 全部以 `agent_run_id` 关联，Task 仅为未来规划领域预留。替代方案是兼容保留 `task_id`；未采用，因为系统尚无对外执行 API 或事件表，当前修正成本最低且能消除语义冲突。

### 2. 一个 POST 同步执行并可直接返回 SSE

`POST /agent-runs` 创建 run 并在当前请求内驱动 kernel；`stream=true` 时直接流出结果。替代方案是 POST 创建后由 worker 执行、GET 订阅；未采用，因为会引入队列、stream 缓存与恢复机制，超出当前 service API 目标。

### 3. Session 只持久化用户可见完成历史

用户输入在 run 启动时提交，assistant 内容仅在成功完成时提交；中间 delta、reflection draft 和 observation 只进入内存状态或安全事件。替代方案是保存全部轨迹为消息；未采用，因为会污染后续上下文并扩大敏感信息面。

### 4. Pattern 返回 Action，Runtime 执行副作用

pattern 只决定下一动作，runtime 统一调用模型/tool port、处理 stream、event 与失败。替代方案是各 pattern 自己运行模型和工具；未采用，因为会重复实现状态、取消与审计，并使动态 pattern 转移不可控。

### 5. ReAct 只依赖最小 Mock Tool Action Port

提供无副作用、确定性的 mock executor 使 ReAct 路径真实完成 action/observation 循环。替代方案是仅测试接口或同步建设完整工具系统；前者不能证明策略闭环，后者超出范围。

## Error Handling And Safety

### API 异常与 HTTP 状态码映射

当前 `BaseError` 统一返回 HTTP 400，不足以区分认证失败、资源不存在与业务冲突。本变更要求 `BaseError` 增加 `http_status: int` 属性（默认 400），子类按语义覆盖：

| 异常类型 | `http_status` | 业务 `code` |
|---|---|---|
| `AuthenticationError` | `401` | `UNAUTHORIZED` |
| `ForbiddenError` | `403` | `FORBIDDEN` |
| `NotFoundError` | `404` | `NOT_FOUND` |
| `AgentRunConflictError` | `409` | `AGENT_RUN_CONFLICT` |
| `ValidationError` | `422` | `VALIDATION_ERROR` |
| `BaseError`（默认） | `400` | 各子类业务码 |

API exception handler 根据 `exc.http_status` 设置 HTTP status code，而非硬编码 400。此修改在前置 `platform-exceptions-foundation` 的 `BaseError` 基类上增加字段，并同步更新 `src/api/exception_handler.py`。`AgentRunConflictError` 作为新增业务异常归入 `src/exceptions/common.py`。

### Runtime 错误策略

| 情况 | Runtime 行为 |
|---|---|
| 非法 session/mode/pattern/action/tool | 外部调用前失败，记录安全错误，不启动后续调用 |
| `ModelError.retryable=true` 且尚无可见 delta | 在 `retry_limit` 内创建新 invocation step；默认限制由配置提供 |
| 有公开可见 delta 或未完成 tool arguments 后 stream 中断 | 不透明重试、不执行残缺工具，run failed |
| `refused` 或 `incomplete` response | 按统一完成语义形成 finish reason；pattern 决定是否完成或失败 |
| cancellation（显式请求或 SSE 断连） | 停止后续 action，标记 cancelled，不提交未完成 assistant message |
| mock tool 校验/执行失败 | 记录安全 tool fact；ReAct 可消费失败 observation，但受 max steps 限制 |

### SSE 断连策略

当 `stream=true` 时，runtime 检测到客户端 SSE 连接关闭后，MUST 将正在执行的 AgentRun 视为取消：停止后续 action，将 run 标记为 `cancelled`，不提交未完成的 assistant message。客户端可通过 `GET /api/v1/agent-runs/{agent_run_id}` 查询 run 终态。与显式 `POST cancel` 的区别仅在触发方式不同，生命周期行为一致。

### 安全边界

- API 入口校验认证、session 归属、mode/pattern 与所有输入 schema。
- Tool action port 当前只注册 mock 工具，禁止命令、文件、网络和外部 credentials。
- Event、step safe metadata 与日志不存储 prompt 全文、raw model body、完整工具参数或逐 delta 输出。
- 仅 `public_output` model action 可产生客户端文本 delta；内部 pattern observation 与工具规划不得通过 SSE 旁路披露。

## Configuration

在现有 settings 模式下增加受控运行配置：

```text
DEFAULT_AGENT_MODE=chat
DEFAULT_CHAT_PATTERN=single_turn
DEFAULT_PLAN_PATTERN=planning
DEFAULT_BUILD_PATTERN=react
DEFAULT_REVIEW_PATTERN=reflection
AGENT_RUN_MAX_STEPS=12
AGENT_RUN_TIMEOUT_SECONDS=120
AGENT_RUN_MODEL_RETRY_LIMIT=1
ENABLE_MOCK_TOOL_ACTIONS=true   # dev/test only
```

真实部署若关闭 mock tool actions，选择需要工具 action 的 ReAct 请求必须在执行前失败，直至后续完整 tools capability 提供 executor。

## Migration Plan

1. 先完成前置 model/event change 中 `RuntimeEvent.task_id -> agent_run_id` 与 metadata 修订，运行现有 contract/model 测试。
2. 新增 contracts、repositories、runtime/pattern/tool port 与 API schema。
3. 通过 Alembic upgrade 创建 `sessions`、`session_messages`、`agent_runs`、`agent_run_steps`、`runtime_events` 及上述约束/索引。
4. 注册 API 路由与 Runtime 依赖，使用 Mock model/tool 完成同步与 SSE 集成测试后再开放真实 OpenAI 路径。
5. 更新文档，明确执行资源不存在 `/tasks` 兼容入口，A2A 外部 task 映射不在本次实现。

回滚时先下线路由和写入，再执行 Alembic downgrade 删除本变更新增表与索引，随后移除新模块；由于不存在既有执行数据迁移，不需要将 AgentRun 回写到 Task。

## Risks / Trade-offs

- [Risk] 同步 SSE 请求在进程退出或客户端断连时缺少跨进程恢复能力。  
  -> Mitigation：首期限定 service API 同步执行，持久化终态与低频事实；worker/resume 另立变更。
- [Risk] 六类 pattern 同时落地会扩大首次实现面。  
  -> Mitigation：所有 pattern 复用同一 action/runtime 通路，并以 Mock Model/Tool 固定集成路径。
- [Risk] 串行 Session 限制会降低并发交互能力。  
  -> Mitigation：通过数据库 partial unique index 保证确定性；并发分支/merge 在后续明确语义后再支持。
- [Risk] Mock tool 被误认为真实工具能力。  
  -> Mitigation：命名、配置、事件和 API 文档均标明 mock-only，无外部副作用。

## Open Questions

- 当前无阻塞实现的问题。断线重连、真实 tools/policy/hooks、summary compaction 和 Task Engine 均明确留待独立变更。
