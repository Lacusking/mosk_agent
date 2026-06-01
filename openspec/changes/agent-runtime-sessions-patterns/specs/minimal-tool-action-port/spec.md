## ADDED Requirements

### Requirement: Runtime 必须通过最小 Tool Action Port 执行动作
系统 MUST 定义 runtime 可调用的工具动作请求与结果契约，输入来自已验证的 `ModelToolCall`，输出可作为 ReAct observation 反馈给模型。

#### Scenario: Mock 工具动作成功执行
- **GIVEN** ReAct 收到名称已注册且参数合法的 mock tool call
- **WHEN** runtime 通过 tool action port 执行动作
- **THEN** executor MUST 返回包含 call id、工具名、成功状态与安全 observation 的结果
- **THEN** runtime MUST 创建对应 step 与审计事件

#### Scenario: 工具参数非法
- **GIVEN** 模型产生的工具参数不符合注册 mock tool schema
- **WHEN** runtime 尝试执行动作
- **THEN** executor MUST 拒绝执行并返回标准化工具校验失败
- **THEN** 系统 MUST NOT 假定工具产生成功 observation

### Requirement: 本变更的 Executor 必须限制为无外部副作用的 Mock 工具
系统 MUST 仅提供确定性的 mock executor 供 ReAct 集成测试，不得执行命令、读写用户文件、访问网络或代表完整工具治理能力。

#### Scenario: 注册的 Mock 工具返回确定结果
- **GIVEN** 测试注册 `mock.echo` 或等价确定性工具
- **WHEN** runtime 以相同有效参数调用该工具
- **THEN** executor MUST 返回可重复验证的 observation
- **THEN** 执行 MUST 不要求外部凭证或网络

#### Scenario: 未注册或外部工具被拒绝
- **GIVEN** 模型请求名称未注册或声明真实外部副作用的工具
- **WHEN** runtime 经由最小 port 请求执行
- **THEN** executor MUST 拒绝该动作
- **THEN** 失败事件 MUST 仅记录安全工具身份和错误分类，不得记录敏感参数

### Requirement: Tool Action 失败必须可被 ReAct 与 Runtime 判定
系统 MUST 区分工具成功 observation、参数/注册错误与执行失败，使 pattern 能结束运行或基于失败 observation 继续，且仍受 `max_steps` 限制。

#### Scenario: 工具失败不会导致无限循环
- **GIVEN** mock executor 返回失败且 ReAct 请求继续
- **WHEN** AgentRun 达到配置的 `max_steps`
- **THEN** runtime MUST 终止运行并返回限制命中的失败原因
- **THEN** 每次动作和终止原因 MUST 可通过运行事件查询

