## ADDED Requirements

### Requirement: 系统必须持久化会话与可见消息历史
系统 MUST 提供持久化 `Session` 与按序排列的 `SessionMessage`，消息历史仅包含用户输入和已完成的 assistant 可见输出。

#### Scenario: 创建会话并记录用户输入
- **GIVEN** 调用方已通过 API Key 认证
- **WHEN** 调用方通过 `POST /api/v1/sessions` 创建会话，并在启动 AgentRun 时提交用户输入
- **THEN** 系统 MUST 返回包含 `session_id`、`status` 与时间字段的统一响应
- **THEN** 用户输入 MUST 以递增 `sequence` 写入该会话历史

#### Scenario: 未认证的会话创建请求被拒绝
- **GIVEN** 请求未携带有效 `Authorization: Bearer <api-key>`
- **WHEN** 调用方请求 `POST /api/v1/sessions`
- **THEN** 系统 MUST 以 HTTP `401` 和业务 `code=UNAUTHORIZED` 返回认证失败响应
- **THEN** 系统 MUST NOT 创建 Session 或 SessionMessage

### Requirement: 系统必须提供可查询的会话历史
系统 MUST 通过 `GET /api/v1/sessions/{session_id}/messages` 提供按 `sequence` 升序返回的用户可见历史，并要求 API Key 认证。

#### Scenario: 查询既有历史
- **GIVEN** 会话包含已提交的 user 与 assistant 消息
- **WHEN** 已认证调用方查询该会话消息
- **THEN** 响应 MUST 包含 `session_id` 及按序排列的消息项
- **THEN** 每条消息 MUST 包含 `message_id`、`sequence`、`role`、内容与可关联的 `agent_run_id`

#### Scenario: 查询不存在的会话
- **GIVEN** `session_id` 不存在
- **WHEN** 已认证调用方查询消息历史
- **THEN** 系统 MUST 以 HTTP `404` 和业务 `code=NOT_FOUND` 返回资源不存在响应

### Requirement: AgentRun 必须基于固定的会话上下文水位
系统 MUST 在创建 AgentRun 时保存 `context_message_sequence`，并只使用该水位及之前的可见历史构造本次输入上下文。

#### Scenario: 新消息不会改变进行中的上下文
- **GIVEN** AgentRun 已记录上下文水位并开始执行
- **WHEN** 会话随后出现新的已提交消息
- **THEN** 该 AgentRun 的模型上下文 MUST NOT 自动纳入水位之后的消息

#### Scenario: 未完成流输出不进入历史
- **GIVEN** AgentRun 已向客户端发送部分文本 delta
- **WHEN** 流被取消或中断且运行未成功完成
- **THEN** 系统 MUST NOT 将部分文本保存为正式 assistant 消息
