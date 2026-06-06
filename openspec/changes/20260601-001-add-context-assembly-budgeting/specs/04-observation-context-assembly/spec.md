## ADDED Requirements

### Requirement: 已完成的工具观察必须可装配到模型上下文
系统 SHALL 将 ReAct 循环中已完成的 tool observation 装配到 ContextBundle.tool_observations，使模型在后续 step 中可以引用之前的工具结果。

#### Scenario: 已完成 tool observation 进入上下文
- **GIVEN** ReAct 在前序 step 中执行了工具动作并得到完成结果
- **WHEN** ContextBuilder 为下一个 step 构造 ContextBundle
- **THEN** 已完成的 tool observation MUST 作为 ContextItem（source=tool, type=observation）出现在 ContextBundle.tool_observations 中
- **AND** observation 内容 MUST 可转换为模型可消费的消息格式
- **AND** 装配顺序 MUST 按原始执行顺序排列

#### Scenario: 未完成或失败的 tool observation 不装配
- **GIVEN** ReAct 中某个工具调用失败或尚在执行中
- **WHEN** ContextBuilder 构造上下文
- **THEN** 该 observation MUST NOT 进入 ContextBundle.tool_observations
- **AND** 失败的 observation 仍保留在 PatternRuntimeState.observations 供 pattern 决策

### Requirement: Observation 必须区分动作决策状态和上下文装配状态
系统 SHALL 保持 PatternRuntimeState.observations 作为 pattern 的动作决策输入，ContextBundle.tool_observations 作为模型上下文的组成部分，两者边界明确。

#### Scenario: Pattern 仍从 PatternRuntimeState 读取 observation
- **GIVEN** ContextBuilder 已将 tool observation 装配到 ContextBundle
- **WHEN** pattern 的 next_action() 被调用
- **THEN** pattern MUST 继续从 PatternRuntimeState.observations 读取动作决策所需信息
- **AND** pattern MUST NOT 直接访问 ContextBundle

#### Scenario: 同一 observation 不重复注入
- **GIVEN** tool observation 同时存在于 PatternRuntimeState.observations 和 ContextBundle.tool_observations
- **WHEN** 模型上下文被最终组装
- **THEN** 该 observation 在模型消息中 MUST 只出现一次
- **AND** ContextBuilder MUST 负责去重逻辑
