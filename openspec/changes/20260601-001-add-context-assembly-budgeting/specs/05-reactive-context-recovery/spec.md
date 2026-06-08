## ADDED Requirements

### Requirement: 系统必须识别模型上下文长度超限错误
系统 SHALL 定义 `ModelContextLengthError` 异常类型，MUST 在 provider 返回 413/context_length_exceeded 时由错误映射器生成。

#### Scenario: Provider 返回 context_length_exceeded
- **GIVEN** 模型请求的上下文超出 provider 的 context window 限制
- **WHEN** provider 返回 413 状态码或 context_length_exceeded 错误
- **THEN** 错误映射器 MUST 生成 `ModelContextLengthError`
- **AND** 错误 MUST 标记 `retryable=true`
- **AND** 错误 MUST 携带 provider 报告的 token 信息（若有）

#### Scenario: 非上下文长度的 413 错误
- **GIVEN** provider 返回 413 但原因不是 context_length_exceeded（如请求体过大）
- **WHEN** 错误映射器处理该错误
- **THEN** 系统 MUST 将其映射为 `ModelInvalidRequestError` 而非 `ModelContextLengthError`

### Requirement: Runtime 必须对上下文超限实施自动恢复
系统 SHALL 在 `decide_model_error()` 中识别 `ModelContextLengthError`，MUST 触发上下文缩减后重试，而不是直接按通用重试逻辑处理。

#### Scenario: 上下文超限触发缩减重试
- **GIVEN** 模型调用返回 `ModelContextLengthError`
- **AND** 当前 AgentRun 尚未在该 step 进行过上下文缩减重试
- **WHEN** runtime 的错误策略评估该错误
- **THEN** runtime MUST 以更激进的裁剪参数重新构造 ContextBundle
- **AND** runtime MUST 使用缩减后的上下文重试模型调用
- **AND** 重试 MUST 记录为可审计事件

#### Scenario: 缩减重试仍失败
- **GIVEN** 上下文缩减后重试的模型调用再次返回 `ModelContextLengthError`
- **WHEN** runtime 评估第二次失败
- **THEN** AgentRun MUST 失败并记录上下文预算不可满足的诊断信息
- **AND** 系统 MUST NOT 进入无限缩减循环

#### Scenario: 已有可见输出时不缩减重试
- **GIVEN** 模型流已向客户端发送部分文本 delta
- **WHEN** runtime 收到 `ModelContextLengthError`（如 streaming 中途失败）
- **THEN** runtime MUST NOT 执行缩减重试
- **AND** AgentRun MUST 失败并保留安全错误信息

### Requirement: 上下文缩减必须采用渐进策略
系统 SHALL 在响应式恢复中使用渐进缩减：先加大 snipCompact 裁剪力度，再应用 microCompact 截断大项，MUST 在每轮缩减后重新校验 token 预算。

#### Scenario: 渐进缩减策略应用顺序
- **GIVEN** 上下文超限需要缩减
- **WHEN** runtime 执行响应式恢复
- **THEN** 系统 MUST 先以更低的 snip 阈值重新裁剪 session messages
- **AND** 若仍超预算，MUST 对剩余大项应用 microCompact 截断
- **AND** 每步缩减后 MUST 重新计算 token 总量
