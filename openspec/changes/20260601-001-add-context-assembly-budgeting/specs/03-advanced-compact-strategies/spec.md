## ADDED Requirements

### Requirement: 系统必须提供 microCompact 策略截断过长内容块
系统 SHALL 提供 microCompact 策略，MUST 将超过配置 token 上限的单个 ContextItem 内容截断为保留首尾的摘要形式，不调用 LLM。

#### Scenario: 截断过长工具结果
- **GIVEN** 某 ContextItem 的 token_count 超过 microCompact 单项上限
- **WHEN** microCompact 策略执行
- **THEN** 策略 MUST 保留内容的首部和尾部片段
- **AND** 中间被截断部分 MUST 以省略标记替代
- **AND** 截断后的 token_count MUST 不超过配置上限

#### Scenario: 短内容不截断
- **GIVEN** ContextItem 的 token_count 未超过上限
- **WHEN** microCompact 策略执行
- **THEN** 策略 MUST 保持该 item 内容不变

### Requirement: 系统必须提供 toolResultBudget 策略限制工具结果总量
系统 SHALL 提供 toolResultBudget 策略，MUST 限制 ContextBundle 中 tool observation items 的总 token 占用，超出时按优先级和时间顺序裁剪。

#### Scenario: 工具结果总量超预算
- **GIVEN** ContextBundle 中 tool observation items 的 token 总和超过 toolResultBudget 配置上限
- **WHEN** toolResultBudget 策略执行
- **THEN** 策略 MUST 按优先级从低到高、时间从早到晚裁剪 tool observation items
- **AND** 裁剪后 tool observation 总 token MUST 不超过配置上限
- **AND** pinned 的 tool observation MUST NOT 被裁剪

#### Scenario: 工具结果在预算内
- **GIVEN** tool observation items 的 token 总和未超过配置上限
- **WHEN** toolResultBudget 策略执行
- **THEN** 策略 MUST 保持所有 tool observation items 不变

### Requirement: 系统必须提供 autoCompact 策略进行 LLM 摘要压缩
系统 SHALL 提供 autoCompact 策略，MUST 在 token 预算紧张时调用 LLM 将被驱逐的中间上下文压缩为临时摘要，该摘要仅用于当前 run，不持久化为 Summary Memory。

#### Scenario: 驱逐内容被 LLM 摘要
- **GIVEN** snipCompact 或 token 预算裁剪移除了中间 session messages
- **AND** autoCompact 策略已启用
- **WHEN** autoCompact 执行
- **THEN** 策略 MUST 将被驱逐内容发送给 LLM 生成摘要
- **AND** 摘要 MUST 作为 ContextItem（source=system, type=summary）插入 ContextBundle
- **AND** 该摘要 MUST NOT 被写入 Summary Memory 或持久化存储

#### Scenario: autoCompact LLM 调用失败
- **GIVEN** autoCompact 的 LLM 摘要调用失败
- **WHEN** 策略处理失败
- **THEN** 系统 MUST 回退到无摘要的裁剪结果继续执行
- **AND** 失败 MUST 记录为可诊断日志
- **AND** AgentRun MUST NOT 因摘要失败而终止
