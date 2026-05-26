## ADDED Requirements

### Requirement: 模型调用必须使用统一跨模块契约
系统 MUST 在 `src.contracts` 中定义公开的模型消息、调用请求、调用响应及能力契约，使 models 与后续 runtime 不依赖 provider 私有结构。

#### Scenario: 统一请求表达模型调用输入
- **GIVEN** 调用方需要向模型提交文本、工具声明或结构化输出要求
- **WHEN** 调用方创建 `ModelRequest`
- **THEN** 请求 MUST 表达 invocation 标识、目标模型、消息内容、可选 provider/protocol、工具、生成选项、streaming 选择和可选调用 timeout
- **THEN** 请求 MUST 可被协议 adapter 转换而无需调用方提供 wire payload

#### Scenario: 非法请求在发送前失败
- **GIVEN** 请求缺少模型名称、消息格式非法或声明了不受支持的选项组合
- **WHEN** 请求被验证或解析为可执行调用
- **THEN** 系统 MUST 拒绝该请求
- **THEN** 系统 MUST NOT 发起外部 provider 调用

### Requirement: 调用 Timeout 必须属于 ModelRequest 执行控制
系统 MUST 将可选 `timeout_seconds` 定义为单次 `ModelRequest` 的调用控制字段，而不是模型生成选项；未提供请求级 timeout 时 MUST 使用 provider/transport 的默认 timeout。

#### Scenario: 请求级 Timeout 覆盖 Provider 默认值
- **GIVEN** provider transport 已配置默认 timeout 且 `ModelRequest` 提供合法的正数 `timeout_seconds`
- **WHEN** models 执行该 invocation
- **THEN** transport MUST 使用 request 指定的 timeout 作为该调用的有效超时
- **THEN** timeout MUST NOT 被作为普通生成参数写入 OpenAI 请求 payload

#### Scenario: 请求未指定 Timeout 时使用默认值
- **GIVEN** provider transport 已配置默认 timeout 且 `ModelRequest` 未提供 `timeout_seconds`
- **WHEN** models 执行该 invocation
- **THEN** transport MUST 使用 provider/transport 默认 timeout

#### Scenario: 调用超时被标准化为模型错误
- **GIVEN** blocking 或 streaming 模型调用达到有效 timeout
- **WHEN** models 处理该超时
- **THEN** 系统 MUST 返回携带 invocation 身份的标准化模型超时或流中断错误
- **THEN** 系统 MUST NOT 返回伪造的成功 `ModelResponse`

### Requirement: 消息内容契约必须支持模型交互所需内容块
系统 MUST 允许统一消息包含文本及模型工具交互需要的结构化内容块，并保留角色语义供不同协议转换。

#### Scenario: 文本与工具结果可作为输入消息表达
- **GIVEN** runtime 需要发送用户文本或已执行工具的结果
- **WHEN** 构造消息内容
- **THEN** contract MUST 表达 `text` 与 `tool_result` 内容块
- **THEN** contract MUST 保留消息角色以供 OpenAI 各协议编码

#### Scenario: Provider 私有 content block 不污染公开基础字段
- **GIVEN** 后续 protocol 需要扩展 provider 特有内容块
- **WHEN** 扩展内容进入公开契约
- **THEN** 系统 MUST 通过受控 custom/typed 扩展表示该内容
- **THEN** 基础文本、工具调用与工具结果语义 MUST 保持稳定

### Requirement: 统一响应必须表达内容、工具意图与停止语义
系统 MUST 将成功模型结果归一化为包含 provider、model、protocol、内容块、工具调用、整体 status、统一 stop reason、原始 stop reason 及可选 usage 的 `ModelResponse`。`status` MUST 表达整体结果状态，`stop_reason` MUST 表达停止或交还控制权的原因。

#### Scenario: 自然完成响应被归一化
- **GIVEN** provider 返回无工具调用的有效最终文本结果
- **WHEN** 协议 adapter 解析结果
- **THEN** `ModelResponse` MUST 包含规范化文本内容与实际 provider/model/protocol
- **THEN** status MUST 表示 `completed`
- **THEN** 统一 stop reason MUST 表示正常完成

#### Scenario: 工具意图作为成功响应返回
- **GIVEN** provider 成功返回一个或多个 function/tool call
- **WHEN** 协议 adapter 解析结果
- **THEN** `ModelResponse` MUST 包含统一的工具调用标识、名称与完成参数
- **THEN** status MUST 表示 `completed`
- **THEN** stop reason MUST 表示 `tool_use`
- **THEN** 工具意图 MUST NOT 被表示为模型异常

#### Scenario: 受控拒绝具有固定状态映射
- **GIVEN** provider 返回可归一化的 refusal 结果
- **WHEN** 协议 adapter 解析结果
- **THEN** `ModelResponse.status` MUST 表示 `refused`
- **THEN** stop reason MUST 表示 `refused`
- **THEN** 该结果 MUST NOT 被表示为 transport 或 protocol 异常

#### Scenario: 不完整响应具有固定状态映射
- **GIVEN** provider 因 max tokens、内容过滤或未知结束原因返回可消费但不完整的结果
- **WHEN** 协议 adapter 解析结果
- **THEN** `ModelResponse.status` MUST 表示 `incomplete`
- **THEN** stop reason MUST 表示具体的截断、过滤或未知原因

#### Scenario: 非法 Status 与 Stop Reason 组合被拒绝
- **GIVEN** 调用方尝试构造 `status=completed` 且 `stop_reason=refused` 或 `max_tokens` 的响应
- **WHEN** contract 校验该 `ModelResponse`
- **THEN** 系统 MUST 拒绝不一致的状态组合

#### Scenario: 未知 provider stop reason 可诊断
- **GIVEN** provider 返回 adapter 尚未认识的停止原因
- **WHEN** 响应被归一化
- **THEN** 系统 MUST 保留原始停止原因
- **THEN** 对可消费但未知的结束结果，统一停止原因 MUST 表示未知且 status MUST 表示 `incomplete`
- **THEN** 无法形成可消费结果的协议失败 MUST 以模型错误表达，而不得静默当作正常完成

### Requirement: Streaming 契约必须可归约为最终响应
系统 MUST 定义模型流事件及归约行为，使 blocking 和 streaming 的最终业务响应使用相同 `ModelResponse` 语义。

#### Scenario: 文本流被归约为最终响应
- **GIVEN** provider 依次发出调用开始、多个文本增量、usage 与完成事件
- **WHEN** reducer 按序消费统一流事件
- **THEN** reducer MUST 组合文本增量并生成最终 `ModelResponse`
- **THEN** 最终 response 的 stop reason 与 usage MUST 与完成流状态一致

#### Scenario: 不完整工具参数不能形成可执行调用
- **GIVEN** streaming 响应正在传递 function arguments 的 JSON 片段
- **WHEN** reducer 尚未接收到对应工具调用完成边界或参数仍非法
- **THEN** 系统 MUST NOT 输出完成的 `ModelToolCall`
- **THEN** 系统 MUST NOT 将该片段表示为可供 runtime 执行的工具意图

#### Scenario: 完成后的工具流被归一化
- **GIVEN** streaming 响应已完成一个工具调用且累计参数可合法解析
- **WHEN** reducer 生成最终响应
- **THEN** 最终 `ModelResponse` MUST 包含已验证的工具调用
- **THEN** stop reason MUST 表示 `tool_use`

### Requirement: Usage 契约必须保存可获得的 token 阶段细分
系统 MUST 对每次模型调用提供统一 usage 结构，覆盖输入、输出、总量以及 provider 可返回的缓存输入、缓存创建与 reasoning 等阶段细分。

#### Scenario: Provider 返回分段 token 统计
- **GIVEN** provider 响应包含输入、输出及更细的缓存或 reasoning token 统计
- **WHEN** adapter 归一化 usage
- **THEN** 系统 MUST 将可映射字段保存至统一 usage
- **THEN** 未标准化但需要诊断的安全字段 MAY 保存在 provider details 中

#### Scenario: Provider 不提供某统计字段
- **GIVEN** provider 响应未返回某个 usage 维度
- **WHEN** adapter 构造统一 usage
- **THEN** 缺失字段 MUST 被表示为未提供而非伪造的零消耗

#### Scenario: 流式 usage 累积完成
- **GIVEN** streaming 调用在一个或多个事件中报告 usage
- **WHEN** reducer 接收到最终完成事件
- **THEN** 最终响应 MUST 携带已归约的稳定 usage 值
