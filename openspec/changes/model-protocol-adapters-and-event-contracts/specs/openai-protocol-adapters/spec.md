## ADDED Requirements

### Requirement: 模型选择必须解耦 provider、protocol 与 model profile
系统 MUST 根据请求和已注册 model profile 选择 provider、wire protocol 与模型能力；同一 provider 下不同模型 MUST 能声明不同协议、选项限制或响应转换行为。

#### Scenario: 同一 Provider 的模型采用不同 profile
- **GIVEN** OpenAI provider 下注册了分别使用 Chat Completions 与 Responses 的模型 profile
- **WHEN** 调用方选择对应模型
- **THEN** selector MUST 解析到该模型声明的 protocol 和 capabilities
- **THEN** 请求 MUST 由选定协议 adapter 编码

#### Scenario: 请求使用模型不支持的能力
- **GIVEN** model profile 声明不支持请求要求的工具、streaming 或结构化输出能力
- **WHEN** selector 验证调用需求
- **THEN** 系统 MUST 在发起 provider 调用之前返回模型能力错误

#### Scenario: 后续厂商可复用或自定义协议
- **GIVEN** 注册了一个非 OpenAI provider profile
- **WHEN** 该 profile 声明 `openai_chat` 或 `custom` protocol
- **THEN** registry MUST 能表示该 provider 与协议的组合
- **THEN** provider 身份 MUST NOT 被用于隐式推断 wire protocol

### Requirement: Adapter 解析与错误映射必须使用安全调用上下文
系统 MUST 在选择 provider、protocol 与 profile 后构建 models 内部的 invocation context，并使用该上下文为响应、流事件与模型错误绑定调用身份及有效 timeout。

#### Scenario: Invocation Context 包含解析所需身份
- **GIVEN** selector 已解析一次可执行模型请求
- **WHEN** protocol adapter 处理响应、流事件或 provider 错误
- **THEN** invocation context MUST 提供 invocation id、provider、model、protocol、profile、streaming 标记与有效 timeout
- **THEN** invocation context MUST NOT 包含凭证、认证 header 或完整消息内容

#### Scenario: 有效 Timeout 由请求覆盖默认配置
- **GIVEN** 请求指定调用 timeout 且 provider 配置存在默认 timeout
- **WHEN** invocation context 被构建
- **THEN** context 中的有效 timeout MUST 使用请求指定值

### Requirement: OpenAI Chat Completions 协议必须支持 blocking 调用
系统 MUST 实现 OpenAI Chat Completions 请求编码和响应归一化，覆盖文本、工具意图、stop reason 与 usage。

#### Scenario: Chat blocking 文本响应成功
- **GIVEN** 已配置有效 OpenAI provider 且模型 profile 使用 `openai_chat`
- **WHEN** provider 返回有效 chat completion 文本响应
- **THEN** adapter MUST 返回统一 `ModelResponse`
- **THEN** 响应 MUST 包含实际模型、正常完成 stop reason 与可获得的 usage

#### Scenario: Chat blocking 返回工具调用
- **GIVEN** 请求声明了工具且 Chat Completions 返回 tool calls
- **WHEN** adapter 解析 completion
- **THEN** adapter MUST 归一化每个工具调用的 id、名称与合法 arguments
- **THEN** 响应 MUST 表示 `tool_use`

#### Scenario: Chat blocking 响应损坏
- **GIVEN** provider 返回缺失关键 choice、非法工具参数或无法解释的结构
- **WHEN** adapter 解析响应
- **THEN** 系统 MUST 返回模型响应解析错误
- **THEN** 系统 MUST NOT 返回部分伪造的完成响应

### Requirement: OpenAI Chat Completions 协议必须支持 streaming 调用
系统 MUST 将 Chat Completions streaming chunks 转换为统一流事件，并支持组合文本、工具参数、usage 与结束原因。

#### Scenario: Chat stream 文本和完成原因被转换
- **GIVEN** OpenAI 返回由文本 chunks 与最终 finish reason 组成的 stream
- **WHEN** adapter 消费该 stream
- **THEN** adapter MUST 发出统一内容增量与完成事件
- **THEN** reducer MUST 可得到与等价 blocking 调用一致的完成语义

#### Scenario: Chat stream 工具参数被安全组合
- **GIVEN** OpenAI 在多个 chunks 中返回 tool call arguments 片段
- **WHEN** adapter 与 reducer 消费这些片段
- **THEN** 片段 MUST 通过统一 tool delta 事件传递
- **THEN** 参数只有在结束并验证后 MUST 才成为完成工具调用

#### Scenario: Chat stream 发生 provider 错误
- **GIVEN** provider 在完成事件前断开或返回流错误
- **WHEN** adapter 处理失败
- **THEN** 系统 MUST 输出或抛出标准化模型 stream failure 语义
- **THEN** 已累积但未完成的工具参数 MUST 不可执行

### Requirement: OpenAI Responses 协议必须支持 blocking 调用
系统 MUST 实现 OpenAI Responses 请求编码和响应归一化，且不得假设其输出结构等同于 Chat Completions。

#### Scenario: Responses blocking 文本输出成功
- **GIVEN** 已配置 OpenAI provider 且模型 profile 使用 `openai_responses`
- **WHEN** Responses API 返回完成的文本 output items
- **THEN** adapter MUST 将文本内容归一化至统一响应
- **THEN** 响应 MUST 包含实际协议身份与完成语义

#### Scenario: Responses blocking function call 输出成功
- **GIVEN** Responses API 返回已完成的 function call output item
- **WHEN** adapter 解析结果
- **THEN** adapter MUST 输出统一工具调用
- **THEN** response MUST 表示工具使用而非最终文本完成

#### Scenario: Responses 返回 incomplete 或 refusal
- **GIVEN** Responses API 返回不完整原因或 refusal output
- **WHEN** adapter 归一化该响应
- **THEN** 系统 MUST 将其映射到对应统一 stop/status 语义
- **THEN** 系统 MUST 保留可诊断的 provider 原始原因

### Requirement: OpenAI Responses 协议必须支持 streaming 调用
系统 MUST 将 Responses 的语义化 streaming events 映射为统一模型流事件，覆盖文本增量、function argument 增量、完成、失败和 usage。

#### Scenario: Responses 文本 stream 被转换
- **GIVEN** provider 发出 response created、output text delta 与 response completed 事件
- **WHEN** adapter 转换事件
- **THEN** adapter MUST 发出调用开始、内容增量和响应完成的统一流事件
- **THEN** reducer MUST 生成最终文本响应

#### Scenario: Responses function arguments stream 被转换
- **GIVEN** provider 发出 function call arguments delta 与 done 事件
- **WHEN** adapter 转换事件
- **THEN** adapter MUST 发出工具调用增量及完成事件
- **THEN** reducer MUST 在参数合法后产生统一工具调用

#### Scenario: Responses failed 事件被映射
- **GIVEN** provider 在 stream 中发出 failed 或 error 事件
- **WHEN** adapter 转换该事件
- **THEN** 系统 MUST 产生标准化失败语义或对应模型错误
- **THEN** 失败信息 MUST 排除敏感请求与认证内容

### Requirement: Mock Provider 必须验证相同公开契约
系统 MUST 提供不依赖外部网络和凭证的 Mock provider，能够覆盖文本、工具意图、usage、失败以及 streaming 归约测试。

#### Scenario: Mock blocking 返回标准响应
- **GIVEN** 测试或本地调用选择 Mock provider
- **WHEN** 发起 blocking 模型调用
- **THEN** Mock MUST 返回满足统一 contract 的确定性响应

#### Scenario: Mock streaming 支持工具路径测试
- **GIVEN** 测试配置 Mock 产生流式工具意图
- **WHEN** 消费 Mock stream
- **THEN** 系统 MUST 可验证 tool delta、tool completion 与最终 `tool_use` 响应行为

### Requirement: 保留的协议不得被误表示为可调用 Provider
系统 MUST 为 `anthropic_messages` 提供协议身份，并为 `custom` 提供符合统一 adapter 契约的抽象注册边界；本变更 MUST NOT 内置 Anthropic 或任意自定义远程 provider 调用实现。

#### Scenario: Anthropic 协议可被识别但不可执行
- **GIVEN** registry 或 profile 引用了 `anthropic_messages`
- **WHEN** 调用方尝试在无已实现 provider adapter 的情况下执行调用
- **THEN** 系统 MUST 返回明确的模型能力或配置错误
- **THEN** 系统 MUST NOT 向 Anthropic endpoint 发起网络请求

#### Scenario: 未注册具体实现的 Custom Profile 不可执行
- **GIVEN** 一个 model profile 声明使用 `custom` protocol，但 registry 中没有注册具体 custom adapter 实现
- **WHEN** 调用方尝试执行该模型调用
- **THEN** 系统 MUST 返回明确的模型能力或配置错误
- **THEN** 系统 MUST NOT 调用任意动态 hook 或未知远程 endpoint

#### Scenario: 注册的 Custom Adapter 必须服从公开契约
- **GIVEN** 后续扩展向 registry 注册符合抽象边界的 custom protocol adapter
- **WHEN** registry 接受该实现
- **THEN** 该 adapter MUST 通过统一 `ModelResponse`、`ModelStreamEvent` 与 `ModelError` 边界与消费者交互
