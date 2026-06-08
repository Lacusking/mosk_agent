## ADDED Requirements

### Requirement: Context bundle construction
系统 SHALL 为每次 AgentRun 构造结构化 ContextBundle，ContextBundle MUST 包含 session messages 槽位，并 MUST 预留 memory summary、tool observations 与 artifacts 槽位。

#### Scenario: Build bundle from session history
- **GIVEN** 一个 active session 已存在多条用户可见 session messages
- **AND** AgentRun 包含固定的 `context_message_sequence`
- **WHEN** runtime 请求构造该 AgentRun 的上下文
- **THEN** 系统 MUST 返回包含水位内 session message items 的 ContextBundle
- **AND** session message items MUST 按原始 sequence 升序排列
- **AND** memory summary、tool observations 与 artifacts 槽位 MUST 存在且允许为空

#### Scenario: Session not found
- **GIVEN** AgentRun 引用的 session 不存在
- **WHEN** runtime 请求构造该 AgentRun 的上下文
- **THEN** 系统 MUST 返回现有资源不存在错误语义
- **AND** 系统 MUST NOT 调用模型
- **AND** 系统 MUST NOT 提交 assistant final message

### Requirement: Context item metadata
系统 SHALL 将每段可装配上下文包装为 ContextItem，并 MUST 提供 source、type、content、priority、token_count、pinned、evictable 与 metadata 字段，以支持后续预算、裁剪和来源治理。

#### Scenario: Session message item metadata
- **GIVEN** 一条 session message 被加入 ContextBundle
- **WHEN** 系统创建对应 ContextItem
- **THEN** ContextItem 的 source MUST 标记为 session
- **AND** ContextItem 的 type MUST 标记为 message
- **AND** ContextItem 的 content MUST 为已转换的 ModelMessage（转换在 builder 构造时完成）
- **AND** ContextItem MUST 记录原始 message sequence
- **AND** `to_model_messages()` MUST 从 content 中提取 ModelMessage 而不再执行格式转换

#### Scenario: Safe metadata only
- **GIVEN** 系统创建任意 ContextItem
- **WHEN** ContextItem 携带 metadata
- **THEN** metadata MUST NOT 包含 authorization、secret、raw provider request 或明文敏感凭据

### Requirement: Runtime uses context builder
系统 SHALL 使 AgentRuntimeKernel 通过 ContextBuilder 获取模型可见上下文，而不是在 kernel 主循环中直接组装 session model context。

#### Scenario: Pattern receives visible context
- **GIVEN** ContextBuilder 为 AgentRun 构造了 ContextBundle
- **WHEN** runtime 创建 PatternRuntimeState
- **THEN** PatternRuntimeState.visible_context_messages MUST 来自 ContextBundle 的模型消息视图
- **AND** 现有 pattern MUST 继续通过 visible_context_messages 读取上下文

#### Scenario: Context conversion failure
- **GIVEN** ContextBundle 中存在无法转换为 ModelMessage 的必需 item
- **WHEN** runtime 准备调用 pattern 或模型
- **THEN** AgentRun MUST 失败并保留可诊断错误类型
- **AND** 系统 MUST NOT 发送模型请求
- **AND** 系统 MUST NOT 提交 assistant final message

### Requirement: Session window context
系统 SHALL 在 ContextBuilder 读取阶段按 AgentRun 固定水位和配置的最近消息数量限制 session message 查询范围，并 MUST 保证进入模型的 session messages 按 sequence 升序。Window 是 builder 的读取参数，不作为 pipeline 策略。

#### Scenario: Window keeps recent messages
- **GIVEN** session 在 AgentRun 水位内有 20 条消息
- **AND** context window 配置为最近 6 条消息
- **WHEN** builder 查询 session messages
- **THEN** ContextBundle MUST 只包含该水位内最近 6 条 session message items
- **AND** 返回 items MUST 按 sequence 升序排列

#### Scenario: Window ignores messages after watermark
- **GIVEN** AgentRun 的 `context_message_sequence` 为 10
- **AND** session 中已存在 sequence 为 11 的后续消息
- **WHEN** 系统构造该 AgentRun 的上下文
- **THEN** ContextBundle MUST NOT 包含 sequence 大于 10 的消息

### Requirement: Snip compact strategy
系统 SHALL 提供无 LLM 调用的 snipCompact 策略，在 session message item 数超过阈值时裁剪中间可驱逐内容，并保留关键和最近上下文。

#### Scenario: Compact long message list
- **GIVEN** ContextBundle 包含超过 snip 阈值的 session message items
- **AND** 配置要求保留头部 2 条和尾部 6 条
- **WHEN** snipCompact 策略执行
- **THEN** 策略 MUST 保留按 sequence 排序的前 2 条 session message items（头部按位置保留）
- **AND** 策略 MUST 保留尾部最近 6 条 session message items
- **AND** 策略 MUST 保留不可驱逐或 pinned 的 items
- **AND** 策略 MUST 移除中间 evictable items 直到满足阈值或无可驱逐 item

#### Scenario: Do not compact short context
- **GIVEN** ContextBundle 中 session message item 数未超过 snip 阈值
- **WHEN** snipCompact 策略执行
- **THEN** 策略 MUST 保持 session message items 不变

#### Scenario: No evictable items remain
- **GIVEN** ContextBundle 超过 snip 阈值
- **AND** 所有超出部分均为 pinned 或不可驱逐 items
- **WHEN** snipCompact 策略执行
- **THEN** 策略 MUST 保留这些 items
- **AND** 系统 MUST NOT 因无法满足阈值而丢弃 pinned 或不可驱逐内容

### Requirement: Strategy pipeline ordering
系统 SHALL 通过 ContextStrategyPipeline 顺序执行上下文策略，并 MUST 使用每个策略输出作为下一个策略输入。

#### Scenario: Pipeline applies strategies in order
- **GIVEN** pipeline 注册了 snipCompact 策略（window 行为在 builder 读取阶段完成）
- **WHEN** 系统构造 AgentRun 上下文
- **THEN** builder MUST 先完成 window 读取并构造 ContextBundle
- **AND** snipCompact MUST 基于 builder 产出的 ContextBundle 执行
- **AND** 最终模型消息视图 MUST 来自 pipeline 输出的 ContextBundle

#### Scenario: Strategy failure stops pipeline
- **GIVEN** pipeline 中某个策略因非法配置失败
- **WHEN** 系统执行 ContextStrategyPipeline
- **THEN** pipeline MUST 停止执行后续策略
- **AND** AgentRun MUST 保留失败状态
- **AND** 系统 MUST NOT 调用模型

### Requirement: Observation ownership boundary
系统 SHALL 保持当前 run 内 ReAct observations 由 PatternRuntimeState.observations 管理，ContextBundle.tool_observations 首期 MUST 为空并仅作为未来跨 step 或跨 run 装配槽位。

#### Scenario: ReAct tool result remains pattern observation
- **GIVEN** ReAct pattern 在当前 AgentRun 内执行了工具动作
- **WHEN** runtime 将工具结果反馈给 pattern
- **THEN** 工具结果 MUST 进入 PatternRuntimeState.observations
- **AND** 该工具结果 MUST NOT 被复制到 ContextBundle.tool_observations

#### Scenario: Empty reserved tool observations slot
- **GIVEN** 系统构造普通 AgentRun 的 ContextBundle
- **WHEN** 没有持久化或待恢复的外部 observation 来源
- **THEN** ContextBundle.tool_observations MUST 为空列表
