## ADDED Requirements

### Requirement: 系统必须以 AgentRun 表达一次 Agent 执行生命周期
系统 MUST 定义由 `agent_run_id` 标识的 AgentRun 及 AgentRunStep，顶层状态至少覆盖 `created`、`running`、`completed`、`failed` 与 `cancelled`，并以 step 记录 pattern 和 invocation 行为。

#### Scenario: 创建运行实例
- **GIVEN** 已认证请求引用有效 Session，并提供输入、`mode` 与可选 `requested_pattern`
- **WHEN** 调用方请求 `POST /api/v1/agent-runs`
- **THEN** 系统 MUST 创建 AgentRun 并返回 `agent_run_id`、`session_id`、`status`、`mode` 与 `trace_id`
- **THEN** AgentRun MUST 以 `agent_run_id` 关联步骤、事件和模型请求 metadata

#### Scenario: 引用不存在的会话
- **GIVEN** 请求提供不存在的 `session_id`
- **WHEN** 调用方创建 AgentRun
- **THEN** 系统 MUST 以 HTTP `404` 和业务 `code=NOT_FOUND` 返回资源不存在响应
- **THEN** 系统 MUST NOT 创建运行实例或写入用户消息

### Requirement: 同一会话的活动运行必须串行化
系统 MUST 在本阶段拒绝同一个 Session 上同时存在多个活动 AgentRun，以保持消息顺序和上下文水位确定性。

#### Scenario: 并发运行被拒绝
- **GIVEN** 会话已有状态为 `created` 或 `running` 的 AgentRun
- **WHEN** 调用方为同一会话创建新的 AgentRun
- **THEN** 系统 MUST 以 HTTP `409` 和业务 `code=AGENT_RUN_CONFLICT` 返回冲突响应
- **THEN** 既有 AgentRun MUST 保持不变

### Requirement: Runtime 必须消费统一模型流并向客户端提供 SSE 输出
系统 MUST 在 `POST /api/v1/agent-runs` 请求包含 `stream=true` 时返回 `text/event-stream`，将统一模型流映射为运行级公开事件，并在完成后保存最终 assistant 消息。

#### Scenario: 流式文本执行成功
- **GIVEN** 已认证请求指定 `stream=true` 且选择的模型支持 streaming
- **WHEN** runtime 消费模型文本增量并完成执行
- **THEN** SSE MUST 至少输出 `run.started`、`output.text.delta` 与 `run.completed` 事件
- **THEN** `run.completed` MUST 包含 `agent_run_id` 与最终状态
- **THEN** `output.text.delta` MUST 仅包含 pattern 标记为用户最终答案阶段的输出
- **THEN** 系统 MUST 仅在完成边界后将聚合后的 assistant 内容写入 Session

#### Scenario: 流请求选择不支持 streaming 的模型
- **GIVEN** AgentRun 需要流式输出但选定模型 profile 不支持 streaming
- **WHEN** runtime 准备执行模型调用
- **THEN** AgentRun MUST 终止为 `failed`
- **THEN** SSE MUST 输出安全的 `run.failed` 事件而不得伪造完成结果

### Requirement: Runtime 必须对模型错误、取消和不完整结果采用确定策略
系统 MUST 根据统一 `ModelError` 与 `ModelResponse` 语义完成 AgentRun 决策，不得将失败或残缺工具意图视为成功输出。

#### Scenario: 可重试错误在可见输出前有限重试
- **GIVEN** 模型调用在未发送可见 delta 前返回 `retryable=true` 错误
- **WHEN** 配置的重试额度尚未耗尽
- **THEN** runtime MUST 创建新的 invocation step 进行有限重试
- **THEN** 每次失败和重试 MUST 形成可审计事件

#### Scenario: 部分输出后的流中断不透明重试
- **GIVEN** 模型流已发出文本 delta 或存在未完成工具参数
- **WHEN** runtime 收到流中断错误
- **THEN** runtime MUST NOT 自动重放该模型输出或执行未完成工具意图
- **THEN** AgentRun MUST 结束为 `failed` 并发出安全失败事件

#### Scenario: 显式取消运行
- **GIVEN** AgentRun 状态为 `created` 或 `running`
- **WHEN** 已认证调用方请求 `POST /api/v1/agent-runs/{agent_run_id}/cancel`
- **THEN** runtime MUST 停止后续 action 并将运行标记为 `cancelled`
- **THEN** 未形成完成响应的内容 MUST NOT 写入 Session

#### Scenario: SSE 客户端断连触发取消
- **GIVEN** AgentRun 以 `stream=true` 执行且客户端 SSE 连接关闭
- **WHEN** runtime 检测到连接断开
- **THEN** runtime MUST 停止后续 action 并将运行标记为 `cancelled`
- **THEN** 取消事件 MUST 记录触发方式为 `sse_disconnect`
- **THEN** 未形成完成响应的内容 MUST NOT 写入 Session
- **THEN** 客户端可通过 `GET /api/v1/agent-runs/{agent_run_id}` 查询终态

### Requirement: 系统必须持久化 AgentRun 的安全事实事件
系统 MUST 将 run、step、pattern、模型生命周期和 mock tool action 的低频事实写入 RuntimeEvent store，并以 `agent_run_id`、`trace_id` 与时间顺序支持查询。

#### Scenario: 查询运行事件
- **GIVEN** AgentRun 已产生事实事件
- **WHEN** 已认证调用方请求 `GET /api/v1/agent-runs/{agent_run_id}/events`
- **THEN** 系统 MUST 返回按发生顺序排列的事件
- **THEN** 事件 MUST NOT 要求保存完整 prompt、provider raw body、完整工具参数或逐 delta 内容
