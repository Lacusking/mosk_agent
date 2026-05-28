## ADDED Requirements

### Requirement: 系统必须将 Mode 与 Pattern 分离并确定性选择策略
系统 MUST 将 `mode` 作为默认行为配置，将 `pattern` 作为可执行决策策略，并按显式 pattern、mode 默认映射、系统 fallback 的顺序选择已注册 pattern。

#### Scenario: 显式 Pattern 覆盖 Mode 默认值
- **GIVEN** AgentRun 指定合法 `requested_pattern` 且其 mode 另有默认 pattern
- **WHEN** selector 选择运行策略
- **THEN** selector MUST 选择显式请求的 pattern
- **THEN** 选择结果 MUST 记录到运行 step 或事件

#### Scenario: 未注册 Pattern 被拒绝
- **GIVEN** 请求指定未注册或不可用的 pattern
- **WHEN** selector 在模型调用前校验请求
- **THEN** AgentRun MUST 失败并报告可诊断的 pattern 选择错误
- **THEN** 系统 MUST NOT 发起模型调用

### Requirement: Pattern 必须通过动作契约由 Runtime 执行
系统 MUST 让 pattern 返回类型化 next action，由 runtime 统一执行模型、工具、流、事件、取消和错误策略；pattern MUST NOT 直接持久化 Session 或绕过 runtime 调用执行端口。

#### Scenario: Pattern 发出模型动作
- **GIVEN** pattern 根据当前运行上下文需要一次模型响应
- **WHEN** pattern 产生 `invoke_model` action
- **THEN** runtime MUST 建立 AgentRunStep 并通过既有 ModelAdapter 执行调用
- **THEN** 模型结果 MUST 作为 observation 回传给 pattern 决定后续动作

#### Scenario: Pattern 请求不允许的动作
- **GIVEN** pattern 产生当前 runtime 未注册的 action 类型
- **WHEN** runtime 校验 action
- **THEN** runtime MUST 拒绝动作并将 AgentRun 标记为失败

#### Scenario: 内部阶段不作为用户输出流出
- **GIVEN** 多阶段 pattern 发出标记为内部用途的路由、工具决策、draft 或 critique 模型动作
- **WHEN** runtime 接收到这些动作的模型文本增量
- **THEN** runtime MUST 将结果仅作为受控 observation 供后续动作使用
- **THEN** runtime MUST NOT 将内部增量映射为客户端 `output.text.delta` 或正式 Session 消息

### Requirement: 系统必须提供六类可执行 Pattern
系统 MUST 为 `single_turn`、`chaining`、`routing`、`planning`、`react` 与 `reflection` 提供可注册和可通过 runtime 完成的策略实现。

#### Scenario: Single Turn 形成最终响应
- **GIVEN** AgentRun 选择 `single_turn`
- **WHEN** 模型返回无工具意图的完成响应
- **THEN** pattern MUST 产生最终完成 action

#### Scenario: Chaining 按 ChainConfig 依序执行阶段
- **GIVEN** AgentRun 选择 `chaining` 且注册了包含至少两个阶段的 `ChainConfig`
- **WHEN** 前一阶段模型调用完成
- **THEN** 后一阶段 MUST 能以前序输出作为受控输入继续执行
- **THEN** 中间 `internal` 阶段的输出 MUST NOT 写入 Session 或流出 SSE
- **THEN** 最后一个阶段 MUST 标记为 `public_output` 并形成最终结果

#### Scenario: Chaining 配置校验
- **GIVEN** `ChainConfig` 只有一个阶段或零个阶段
- **WHEN** selector 校验 pattern 可执行性
- **THEN** 系统 MUST 拒绝该 pattern 并返回校验错误
- **THEN** 系统 MUST NOT 发起模型调用

#### Scenario: Routing 通过配置规则转移
- **GIVEN** AgentRun 选择 `routing` 且用户输入匹配某条配置规则
- **WHEN** 路由评估完成
- **THEN** runtime MUST 以命中规则的 `target_pattern` 产生 `TransitionPatternAction`
- **THEN** 系统 MUST NOT 为此发起模型调用

#### Scenario: Routing 通过模型 fallback 分类转移
- **GIVEN** AgentRun 选择 `routing`，无配置规则命中，且 `model_fallback=true`
- **WHEN** 受控模型调用返回 `allowed_targets` 内的有效 pattern 名称
- **THEN** runtime MUST 记录 pattern transition 并继续执行目标 pattern
- **THEN** 路由模型调用 MUST 标记为 `internal`，不产生用户可见输出

#### Scenario: Routing 模型返回非法目标
- **GIVEN** 模型分类返回不在 `allowed_targets` 或未注册的 pattern 名称
- **WHEN** routing 校验模型输出
- **THEN** run MUST 以失败终止
- **THEN** 系统 MUST NOT 将未注册 pattern 名称传递给 runtime 执行

#### Scenario: Planning 以结构化文本完成
- **GIVEN** AgentRun 选择 `planning`
- **WHEN** 模型以规划专用 system prompt 引导后返回完成响应
- **THEN** 系统 MUST 以该文本作为 `public_output` 完成本次运行
- **THEN** 系统 MUST NOT 创建 Task、todo、reminder 或 Markdown plan 文件
- **THEN** 系统 MUST NOT 动态将计划步骤转化为 chaining stages 或其他 pattern 执行链

#### Scenario: ReAct 消费工具观察继续生成
- **GIVEN** AgentRun 选择 `react` 且模型产生合法 mock tool 意图
- **WHEN** runtime 执行 tool action 并回传 observation
- **THEN** ReAct MUST 能继续模型循环并通过公开最终答案阶段形成响应，或命中运行限制

#### Scenario: Reflection 使用审阅结果修订答案
- **GIVEN** AgentRun 选择 `reflection`
- **WHEN** draft 与 critique 两个阶段形成有效结果
- **THEN** pattern MUST 使用受控 critique 触发修订并输出最终响应
- **THEN** draft 与 critique MUST NOT 作为用户可见文本流输出
