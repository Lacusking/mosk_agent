## ADDED Requirements

### Requirement: 系统必须定义统一 RuntimeEvent envelope
系统 MUST 在 `src.contracts` 中定义可供后续 runtime 与事件基础设施消费的 `RuntimeEvent` envelope，包含事件身份、版本、`agent_run_id`/step 关联、trace/span 关联、actor、发生时间及类型化 payload。

#### Scenario: 模型生命周期事件可被序列化
- **GIVEN** 一次模型调用拥有 invocation、agent run 与 trace 上下文
- **WHEN** 调用方构造模型相关 `RuntimeEvent`
- **THEN** event MUST 包含事件类型、版本、关联标识、trace/span 和 created-at 信息
- **THEN** payload MUST 符合所选模型事件类型的公开 schema

#### Scenario: 非法 payload 被拒绝
- **GIVEN** 调用方为模型完成事件提供缺少必填 usage/stop/status 语义的非法 payload
- **WHEN** event contract 执行验证
- **THEN** 系统 MUST 拒绝该事件对象
- **THEN** 错误 MUST 定位到非法事件 payload 字段

### Requirement: 系统必须定义模型调用生命周期事实事件
系统 MUST 定义模型调用开始、完成、失败及产生工具调用意图的 durable event 类型，使后续 runtime 可以记录模型 step 的可观测事实。

#### Scenario: 模型调用开始事件描述调用边界
- **GIVEN** runtime 准备开始一次已选择 profile 的模型调用
- **WHEN** 构造 `ModelInvocationStarted` payload
- **THEN** payload MUST 表达 invocation id、provider、model、protocol、profile 与是否 streaming

#### Scenario: 成功模型调用完成事件包含使用量与停止原因
- **GIVEN** 模型调用返回统一成功响应
- **WHEN** 构造 `ModelInvocationCompleted` payload
- **THEN** payload MUST 表达 status、标准化 stop reason、可用的 provider 原始原因、usage、latency 与工具调用数量
- **THEN** `tool_use` 返回 MUST 能作为成功完成事实表达

#### Scenario: 完成事件保留 Status 与 Stop Reason 的合法映射
- **GIVEN** 模型返回 `completed/tool_use`、`incomplete/max_tokens` 或 `refused/refused` 的合法响应组合
- **WHEN** 构造 `ModelInvocationCompleted` payload
- **THEN** event payload MUST 保留该整体状态与停止原因组合
- **THEN** event contract MUST 拒绝与模型响应契约不一致的组合

#### Scenario: 失败模型调用事件包含决策字段
- **GIVEN** models 层返回标准化 `ModelError`
- **WHEN** 构造 `ModelInvocationFailed` payload
- **THEN** payload MUST 表达错误分类、retryable、fallback allowed、可用 provider code/status 与 latency

#### Scenario: 工具调用意图事件仅记录安全事实
- **GIVEN** 统一模型响应包含一个或多个完成工具调用
- **WHEN** 构造 `ModelToolCallsProduced` payload
- **THEN** payload MUST 表达 invocation、call id、工具名称和参数校验状态
- **THEN** payload MUST NOT 要求存储完整未脱敏参数

### Requirement: 模型流事件与 durable runtime event 必须具有明确边界
系统 MUST 将高频模型内容/工具参数增量定义为 `ModelStreamEvent`，而不是要求将每个 delta 表示为 durable `RuntimeEvent`。

#### Scenario: 内容增量仅作为实时模型事件传递
- **GIVEN** 一次 streaming 响应生成多个文本增量
- **WHEN** adapter 输出这些增量
- **THEN** 增量 MUST 可通过 `ModelStreamEvent` 被消费者处理
- **THEN** 本变更定义的 durable model lifecycle events MUST NOT 要求逐 token 或逐 delta 记录

#### Scenario: 流式调用完成可转化为生命周期事实
- **GIVEN** streaming reducer 已归约得到最终 `ModelResponse`
- **WHEN** 后续 runtime 需要记录结果
- **THEN** 该响应 MUST 提供构造 `ModelInvocationCompleted` 或 `ModelToolCallsProduced` 所需字段

### Requirement: 事件契约不得要求持久化敏感模型载荷
模型事件 payload MUST 以可观测与审计所需的最小信息为界，不得要求存储凭证、完整 raw provider request/response、完整 prompt 或未脱敏工具参数。

#### Scenario: 调用完成事件保存最小可观测字段
- **GIVEN** 模型响应包含文本、usage、停止原因与 provider 元数据
- **WHEN** 创建完成事件 payload
- **THEN** payload MUST 能记录 provider/model/protocol、usage、stop、latency 与状态
- **THEN** payload MUST NOT 要求复制完整文本响应或原始 wire body

### Requirement: 本变更只定义事件而不提供事件存储行为
系统 MUST 在本变更中提供 event schema 与事件类型定义，但 MUST NOT 要求 Event Store、Event Bus、replay query 或持久化 migration 作为验收条件。

#### Scenario: 事件 contract 在无数据库情况下可验收
- **GIVEN** 开发或测试环境没有 runtime_events 数据表和事件存储服务
- **WHEN** 执行本 capability 的测试
- **THEN** 系统 MUST 能验证事件构造、校验与序列化行为
- **THEN** 测试 MUST NOT 依赖数据库 migration 或事件写入服务
