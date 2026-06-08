## ADDED Requirements

### Requirement: 系统必须支持基于 token 的上下文预算
系统 SHALL 为每次模型调用提供 token 级别的上下文预算校验，MUST 在发送请求前验证装配后的上下文不超过目标模型的 context window。

#### Scenario: 预飞行 token 校验通过
- **GIVEN** ContextBundle 装配完成且已计算 token 总量
- **AND** 目标模型的 context window 为 128000 tokens
- **AND** 装配后上下文 token 总量为 5000
- **WHEN** ContextBuilder 执行预飞行校验
- **THEN** 系统 MUST 允许该上下文进入模型调用
- **AND** 系统 MUST 记录预估 token 使用量用于诊断

#### Scenario: 预飞行 token 校验失败触发裁剪
- **GIVEN** ContextBundle 装配后 token 总量超过目标模型 context window 减去输出预留空间
- **WHEN** ContextBuilder 执行预飞行校验
- **THEN** 系统 MUST 触发 token 级裁剪策略
- **AND** 裁剪后上下文 MUST 符合 token 预算
- **AND** 系统 MUST NOT 在裁剪后丢弃 pinned 或不可驱逐 item

#### Scenario: 无法在预算内满足最小上下文
- **GIVEN** 即使裁剪所有可驱逐 item 后 token 总量仍超预算
- **WHEN** ContextBuilder 完成裁剪
- **THEN** 系统 MUST 返回可诊断的上下文预算错误
- **AND** AgentRun MUST 失败
- **AND** 系统 MUST NOT 发送模型请求

### Requirement: 系统必须提供可插拔的 token 计数器
系统 SHALL 定义 `TokenCounter` 协议，MUST 支持默认的字符长度估算实现和可选的精确 tokenizer 实现。

#### Scenario: 默认估算器计算 token
- **GIVEN** 系统未配置精确 tokenizer
- **WHEN** 系统计算 ContextItem 的 token 数
- **THEN** 系统 MUST 使用字符长度估算（如 len/4）
- **AND** 估算结果 MUST 为正整数

#### Scenario: 精确 tokenizer 计算 token
- **GIVEN** 系统配置了 tiktoken 或等价 tokenizer
- **WHEN** 系统计算 ContextItem 的 token 数
- **THEN** 系统 MUST 使用配置的 tokenizer
- **AND** 结果 MUST 反映模型实际 token 消耗

### Requirement: ModelProfile 必须声明 context window 容量
系统 SHALL 在 `ModelProfile` 中增加 `context_window_tokens` 字段，MUST 用于预飞行校验和 token 预算计算。

#### Scenario: Profile 声明 context window
- **GIVEN** 注册了 context_window_tokens 为 128000 的模型 profile
- **WHEN** ContextBuilder 为该模型构造上下文
- **THEN** 预飞行校验 MUST 使用 128000 作为 token 上限
- **AND** 输出预留空间 MUST 从该上限中扣除

#### Scenario: Profile 未声明 context window
- **GIVEN** 模型 profile 未设置 context_window_tokens
- **WHEN** ContextBuilder 构造上下文
- **THEN** 系统 MUST 使用配置的全局默认 token 预算
- **AND** 系统 MUST NOT 跳过 token 校验
