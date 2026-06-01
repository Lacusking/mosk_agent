## 背景（Context）

当前仓库已完成基础目录、配置、ORM 基础模型以及 `src.core.errors` 的初始实现，但 `src/models`、`src/events` 与 `src/runtime` 仍处于模块骨架阶段。项目基线要求：

- `models` 向 runtime 提供统一的模型调用结果，而不是暴露某家厂商的原始响应结构。
- `events` 作为后续审计、观测和回放的事实入口。
- 模块间共享的数据必须通过 `src/contracts` 中明确的 schema 传递。

现有 LLD 对模型能力的描述主要面向单一 OpenAI adapter 与简单的 `ModelResponse`。在真正实现 agent runtime 之前，需要先解决以下边界问题：

1. `provider`、传输协议 `protocol` 与模型能力 `profile` 不是同一概念。同一 provider 下，不同模型可能使用不同 API 形式、接受不同参数或返回不同结构；非 OpenAI 厂商也可能兼容某类 OpenAI 协议。
2. blocking 与 streaming 不是简单的返回方式差异。streaming 中会逐步出现文本、tool arguments、usage 和停止原因，必须能够归约成与 blocking 同语义的最终响应。
3. runtime 不应识别 provider SDK 的异常类名或厂商原始字符串。它需要稳定的响应、错误与事件契约，以决定结束、执行工具、重试或失败。

本变更继续遵守真实远程 provider 的 MVP 边界：实际调用实现仅覆盖 OpenAI 与 Mock；Anthropic 仅预留 protocol 扩展边界，不发起 Anthropic 调用。

本变更将 streaming 提前纳入实现范围。原因是 tool call、stop reason、usage 与事件契约均受流式行为影响；若先仅按 blocking 定义公开 contract，后续实现 stream 时会改变 runtime 所依赖的数据边界。

## 目标与非目标（Goals / Non-Goals）

**目标：**

- 建立 `src/exceptions` 作为平台正式异常入口，并定义 runtime 可判定的模型专属错误层级。
- 在 `src/contracts` 建立模型调用公开契约，覆盖消息、工具调用、生成选项、blocking response、stream event、stop reason 与 token usage 分段信息。
- 将 `provider`、`protocol` 与 `model profile` 解耦，支持同一 provider 下的不同模型处理规则。
- 实现 OpenAI Chat Completions、OpenAI Responses 与 Mock 三条可执行 adapter 路径。
- 对 OpenAI Chat Completions 与 OpenAI Responses 同时支持 blocking 和 streaming 调用。
- 为每次调用提供可覆盖 provider 默认值的 timeout 控制，并将超时统一映射为模型错误。
- 定义模型生命周期相关的 `RuntimeEvent` envelope 与类型化 payload，供后续 runtime 与 Event Store 消费。
- 为 `anthropic_messages` 与 `custom` 定义协议扩展身份和接口边界，但不声明其具备当前可调用能力。

**非目标：**

- 不实现 Anthropic、Gemini、Ollama 或其他第三方远程 provider 调用。
- 不实现 runtime event loop、tool executor、Event Store、Event Bus 或 replay。
- 不新增 API/CLI 对外模型调用或流式接口。
- 不实现跨调用 token/cost 聚合、pricing、budget enforcement、自动重试或自动 provider fallback。
- 不持久化完整 prompt、原始 provider 请求/响应或高频文本 delta。

## 架构（Architecture）

### 分层关系

```text
未来的 Prompt / Runtime 消费者
              |
              | ModelRequest / ModelStreamEvent / ModelResponse
              v
+-------------------------- contracts ---------------------------+
| 公共 schema：message、tool、usage、stop reason、runtime event   |
+-----------------------------------------------------------------+
              |
              v
+---------------------------- models ----------------------------+
| Selector -> Provider Registration -> ModelProfile              |
|                                |                                |
|                                v                                |
| Protocol Adapter: openai_chat | openai_responses               |
|                   anthropic_messages（预留） | custom（预留）    |
|                                |                                |
| Transport / Parser / Streaming Reducer                         |
+-----------------------------------------------------------------+
              |
              | 发生标准化失败时抛出
              v
+-------------------------- exceptions --------------------------+
| BaseError -> ModelError -> 可重试 / 不可重试的具体类型            |
+-----------------------------------------------------------------+
              |
              | 后续 runtime 根据结果或错误构造事实事件
              v
+---------------------- contracts.runtime_events ----------------+
| RuntimeEvent envelope + 模型生命周期 typed payload              |
+-----------------------------------------------------------------+
```

### 模型调用流程

```text
ModelRequest
  -> 校验公开输入与请求能力
  -> selector 解析 provider + model profile + protocol
  -> protocol encoder 生成厂商 wire payload
  -> provider transport 发送 blocking 请求或读取 SSE stream
  -> protocol parser 将响应或流事件映射为统一 contracts
  -> streaming reducer 汇聚文本、工具调用、usage 与 stop reason
  -> 返回 ModelResponse，或抛出 ModelError
```

### 模块所有权

| 模块 | 所有权 | 不承担的职责 |
|---|---|---|
| `src/contracts` | 公开的数据契约与事件 payload | 不转换 provider wire body |
| `src/exceptions` | 平台和模型标准错误语义 | 不决定 runtime 重试策略 |
| `src/models` | 模型选择、协议编解码、流归约、错误映射 | 不执行工具、不持久化事件 |
| `src/events` | 暴露事件类型/契约的发现入口 | 本次不实现 store/bus/replay |
| 后续 `src/runtime` | 消费模型结果并进行步骤流转 | 不解析 provider 私有响应 |
| 后续 `src/observability` | 聚合 usage、latency 与成本 | 不改变单次模型响应语义 |

models 模块在本次变更中不写入 durable event，因为 runtime 与 Event Store 尚不在本次实现范围。它必须输出足以构造模型生命周期事件的标准化响应和错误字段，使后续 runtime 无需检查 provider 原始 body。

## 组件（Components）

### `src/exceptions`：正式异常入口

`src/exceptions` 替代 `src/core/errors.py` 成为平台异常定义的正式归属位置：

```text
exceptions/
├── __init__.py
├── base.py       # BaseError
├── common.py     # ValidationError、鉴权/权限/配置错误
├── storage.py    # StorageError
└── models.py     # ModelError 及模型专属子类
```

当前 API exception handler、鉴权依赖、`src/core/__init__.py` 与相关测试都迁移为引用 `src.exceptions`。按已确认决策，不保留 `src.core.errors` 的兼容导出层。

`BaseError` 增加 `http_status: int` 属性（默认 400），子类按语义覆盖。API exception handler 根据 `exc.http_status` 设置 HTTP 状态码，取代当前对所有 `BaseError` 硬编码 HTTP 400 的行为。现有公共异常的映射：`AuthenticationError -> 401`、`ForbiddenError -> 403`、`NotFoundError -> 404`、`ValidationError -> 422`。后续变更可在此基础上增加业务异常（如 `AgentRunConflictError -> 409`）。

模型公开错误分类如下：

| 错误类型 | `retryable` | 后续 runtime 的典型判断 |
|---|---:|---|
| `ModelConfigurationError` | `false` | 调用前失败，终止或按显式配置处理 |
| `ModelAuthenticationError` | `false` | 不重试；提示凭证配置问题 |
| `ModelAuthorizationError` | `false` | 不重试；终止 |
| `ModelRateLimitError` | `true` | 可依据 `retry_after_seconds` 延迟重试 |
| `ModelTimeoutError` | `true` | 可有限重试 |
| `ModelUnavailableError` | `true` | 可重试或由后续策略 fallback |
| `ModelInvalidRequestError` | `false` | 调整输入或 profile，不盲目重试 |
| `ModelCapabilityError` | `false` | 重新选择支持目标能力的模型或失败 |
| `ModelResponseParseError` | 默认 `false` | 报告协议或响应兼容性问题 |
| `ModelStreamInterruptedError` | 条件判定 | 根据已产生内容/工具状态决定后续动作 |
| `ModelSafetyError` | `false` | 返回受控拒绝或策略终止 |

`ModelError` 应携带的标准化决策字段：

```text
provider?
model?
protocol?
operation?                 # invoke / stream / parse / select
retryable
fallback_allowed
provider_error_code?
provider_status_code?
retry_after_seconds?
sanitized_data?
```

这些字段用于后续 runtime 判断，不包含 credentials、authorization headers 或未经清洗的原始 body。

### `src/contracts/runtime`：模型运行时跨模块公开 schema

数据库 ORM contract 已归入 `src/contracts/database`。本次新增的模型运行时 contract
归入独立子包，以免持久化映射与 runtime 协议混放：

```text
contracts/
├── database/         # ORM 基础模型与数据库类型
└── runtime/
    ├── messages.py   # ModelMessage 与 content blocks
    ├── models.py     # capabilities、options、request/response、tool、usage、stream
    └── events.py     # RuntimeEvent envelope 与模型生命周期 payload
```

模型工具声明和模型返回的 tool-call intent 暂时归属 `contracts/runtime/models.py`。它们描述模型交互协议，而非工具执行权限或 sandbox 行为；后续工具系统可复用这些公开类型。

### `src/models`：模型 adapter 层

```text
models/
├── base.py                 # ModelAdapter / ProtocolAdapter 接口
├── registry.py             # provider、protocol 与 profile 注册表
├── selector.py             # 从请求解析可执行 provider/profile/protocol
├── profiles.py             # 模型级能力、协议选择与受控覆盖规则
├── capabilities.py         # capability 定义与调用前校验
├── options.py              # 统一生成参数处理
├── streaming.py            # ModelStreamReducer
├── transport/
│   ├── http.py             # blocking 与 SSE HTTP 边界
│   └── auth.py             # provider credential/header 构建
├── protocols/
│   ├── openai_chat.py      # 实现
│   ├── openai_responses.py # 实现
│   ├── anthropic_messages.py # 仅协议预留，不可远程调用
│   └── custom.py           # 自定义协议 adapter 抽象与注册边界
├── providers/
│   ├── openai.py           # OpenAI provider 注册与调用配置
│   └── mock.py             # 确定性测试/本地 provider
└── parsers/
    ├── tool_calls.py       # tool call 与参数片段归一化
    ├── stop_reason.py      # provider 停止语义映射
    ├── usage.py            # token usage 映射
    └── errors.py           # provider 失败到 ModelError 的映射
```

项目已依赖 `httpx`。本次优先使用统一 HTTP transport，而不新增 provider SDK 依赖。这样 OpenAI Chat 与 Responses 的 wire payload、SSE 事件与错误映射均能显式实现，并通过 fake HTTP/SSE fixture 进行确定性测试。

### `src/events`：事件发现入口

本次不实现事件基础设施。`src/events/__init__.py` 可暴露模型事件类型或公开 contracts 以便后续模块发现，但事件 schema 的正式归属为 `src/contracts/runtime/events.py`。

## 接口（APIs）

本变更不新增对外 HTTP API 或 CLI 命令。新增接口均为内部公共 Python contract 与 adapter interface。

### ModelAdapter 接口

```python
class ModelAdapter(Protocol):
    async def invoke(self, request: ModelRequest) -> ModelResponse: ...
    async def stream(self, request: ModelRequest) -> AsyncIterator[ModelStreamEvent]: ...
```

- `invoke()` 与 `stream()` 接收相同的、已经过 schema 验证的 `ModelRequest`。
- `invoke()` 返回完整 `ModelResponse`。
- `stream()` 输出标准化 `ModelStreamEvent`；消费者可将其交给 `ModelStreamReducer`，得到与 blocking 路径同形的最终 `ModelResponse`。
- `request.timeout_seconds` 是本次 invocation 的超时上限；为空时采用 provider/transport 配置的默认超时。timeout 属于调用控制而非模型生成选项，因此不进入 `ModelOptions`，也不写入 provider wire payload，除非某 provider 协议本身另有显式需求。

### ProtocolAdapter 接口

```python
class ProtocolAdapter(Protocol):
    protocol: ModelProtocol

    def build_payload(
        self, request: ModelRequest, profile: ModelProfile
    ) -> dict[str, object]: ...

    def parse_response(
        self, response: object, context: InvocationContext
    ) -> ModelResponse: ...

    def parse_stream_event(
        self, event: object, context: InvocationContext
    ) -> ModelStreamEvent | None: ...

    def map_error(
        self, error: object, context: InvocationContext
    ) -> ModelError: ...
```

协议层负责 wire format；provider 层负责 endpoint、credential 与 transport 实例；profile 层负责某模型选用哪个协议以及支持哪些标准能力。

### InvocationContext 内部上下文

`InvocationContext` 是 `src/models` 内部只读上下文，不属于跨模块公开 contract。它由 selector 在 profile 与有效调用配置解析完成后构建，并传给 parser/error mapper，使解析结果和异常都能绑定到同一次 invocation，而不读取完整请求正文。

```text
InvocationContext
  invocation_id
  provider
  model
  protocol
  profile_name
  capabilities
  streaming
  effective_timeout_seconds
  started_at
  safe_metadata                # 可记录、已过滤的诊断元数据
```

约束：

- 不包含 API key、authorization header、完整 messages、完整 tool arguments 或 wire payload。
- `effective_timeout_seconds` 由 `ModelRequest.timeout_seconds` 覆盖 provider/transport 默认值后确定。
- `parse_response` 使用它填充响应身份和协议来源；`parse_stream_event` 使用它绑定 stream sequence 所属 invocation；`map_error` 使用它填充标准错误的 provider/model/protocol/operation 信息。

### Selector 接口语义

```text
request.provider / request.model / request.protocol
    + provider registrations
    + model profiles
    -> ProviderRegistration
    -> ModelProfile
    -> ProtocolAdapter
```

profile 可以声明：

```text
provider
model_pattern
protocol
capabilities
allowed/unsupported options
受控 request/response/stream transform hook
```

profile 只允许影响 provider 侧 payload 与转换逻辑，不允许改变 `ModelResponse`、`ModelStreamEvent` 或 `RuntimeEvent` 的公开形状。

### `custom` 协议最小扩展形态

本次 `custom.py` 不提供任意 hook，也不包含可调用远程实现；它定义一个供后续 provider 实现继承/注册的 `CustomProtocolAdapter` 抽象边界。该抽象遵循 `ProtocolAdapter` 的 `build_payload`、`parse_response`、`parse_stream_event` 与 `map_error` 方法，并以注册实例作为可执行性的唯一依据。

```text
ModelProtocol.CUSTOM                     # 可声明的协议身份
CustomProtocolAdapter(ProtocolAdapter)   # 抽象扩展边界
ProtocolRegistry.register(adapter)       # 注册具体实现后方可执行
```

- 仅将 profile 声明为 `custom`，但没有注册具体 adapter 时，selector 必须报 `ModelCapabilityError` 或 `ModelConfigurationError`。
- 本次内置 provider 不注册任何可执行 `custom` adapter。
- 该扩展点只能产生统一 `ModelResponse` / `ModelStreamEvent` / `ModelError`，不能绕过公开 contracts。

### 预留协议行为

`anthropic_messages` 提供可声明的 protocol identity；`custom` 提供上述抽象注册边界。若请求选择了尚无实际 provider adapter 的协议，系统必须明确抛出 `ModelCapabilityError` 或 `ModelConfigurationError`，不能静默 fallback 为 OpenAI/Mock，也不能发起未知远程网络请求。

## 数据模型（Data Model）

### 模型消息

```text
ModelMessage
  role: system | developer | user | assistant | tool
  content: list[ModelContentBlock]

ModelContentBlock
  kind: text | image | tool_call | tool_result | refusal | custom
  根据 kind 具有相应类型化字段
```

content block 的目的不是暴露厂商 body，而是让 runtime 能在 provider 之间表达稳定的文本和工具交互内容。`custom` 仅作为受控扩展点，不能替代基础工具/文本语义。

### 请求与响应

```text
ModelRequest
  invocation_id
  provider?
  model
  protocol?
  messages
  tools
  tool_choice?
  response_format?
  options
  stream
  timeout_seconds?            # invocation 级调用超时；正数
  metadata

ModelResponse
  invocation_id
  provider
  model
  protocol
  content
  tool_calls
  stop_reason
  provider_stop_reason?
  usage?
  status: completed | incomplete | refused

ModelToolCall
  call_id
  name
  arguments: dict[str, object]
  provider_call_id?
```

`raw` provider response 不作为默认公开 contract 字段。完整原始内容可能包含敏感信息，也会让后续模块耦合 provider wire shape。

### Timeout 归属与解析顺序

timeout 属于 invocation 的执行控制，不属于厂商生成参数，因此定义在 `ModelRequest.timeout_seconds`，不放入 `ModelOptions`。

```text
ModelRequest.timeout_seconds（若提供）
             |
             v 覆盖
Provider / Transport default timeout
             |
             v
InvocationContext.effective_timeout_seconds
             |
             v
HTTP blocking 请求或整个 stream 读取边界
```

规则：

- `timeout_seconds` 可为空；提供时必须为正数。
- request 级 timeout 优先于 provider/transport 默认 timeout。
- 后续 runtime 若有 agent run deadline 或 policy 上限，可以在创建 `ModelRequest` 前限制请求 timeout；本变更不实现该 runtime 策略。
- 超时不发送为 OpenAI 请求 body 的生成参数，而是在 transport 执行边界生效。
- blocking 或 streaming 达到有效超时后，models 抛出 `ModelTimeoutError`，包含已解析的 invocation identity；stream 若已有增量输出，可用 `ModelStreamInterruptedError` 表达部分输出状态并将根因为 timeout 纳入安全诊断字段。

### 模型能力与选项

```text
ModelCapabilities
  tool_calling
  streaming
  structured_output
  vision
  reasoning

ModelOptions
  temperature?
  max_output_tokens?
  top_p?
  stop_sequences?
  parallel_tool_calls?
  provider_options?        # 受控、非核心扩展
```

selector 在请求发往 provider 前校验 capability 与 option policy。例如 profile 不支持 tool calling 或不允许某生成参数时，应抛出 `ModelCapabilityError` 或 `ModelInvalidRequestError`。`ModelOptions` 仅表达影响模型生成语义的选项，不包含 `timeout_seconds`。

### Usage 统计

```text
ModelUsage
  input_tokens?
  output_tokens?
  total_tokens?
  cached_input_tokens?
  cache_creation_input_tokens?
  reasoning_tokens?
  provider_details: dict[str, object]
```

规则：

- usage 描述一次模型 invocation 的实际或 provider 报告统计，不负责任务级聚合。
- provider 未返回的维度保持为空，不可用假造的 `0` 表示“没有消耗”。
- 可标准化的缓存或 reasoning 分段进入显式字段；安全但暂未标准化的 provider usage 明细可进入 `provider_details`。
- pricing 与 cost aggregation 不在本次范围。

### Streaming 事件与归约

```text
ModelStreamEvent
  invocation_id
  event_type:
    invocation_started
    content_delta
    tool_call_started
    tool_call_delta
    tool_call_completed
    usage_updated
    response_completed
    response_failed
  sequence
  payload: 对应事件类型的 typed payload
```

归约过程：

```text
invocation_started
      |
      +--> content_delta* ------------------------+
      |                                           |
      +--> tool_call_started                      |
             -> tool_call_delta*                  |
             -> tool_call_completed               |
      |                                           v
      +--> usage_updated*                ModelStreamReducer
      |                                           |
      +--> response_completed --------------------+
      |                                           v
      +--> response_failed ----------------> ModelError
                                       成功完成时生成 ModelResponse
```

工具参数流的安全边界：

- `tool_call_delta.arguments_delta` 为待累积字符串片段。
- 参数片段未完成时，不构成 `ModelToolCall`，也不可交给 runtime 执行。
- 只有工具调用完成且 JSON/schema 校验通过后，reducer 才产出完成的统一工具调用。
- 流在工具参数完成前中断时，必须以 stream interruption 处理，不可执行残缺意图。

### Response Status 与 Stop Reason 分工

`status` 与 `stop_reason` 不表达同一个维度：

- `status` 表达本次 provider response 是否形成可消费的整体结果：正常完成、带限制的不完整结果、或受控拒绝。
- `stop_reason` 表达模型为何停止生成或为何将控制权交还 runtime，用于决定下一动作，例如调工具或处理截断。
- transport/protocol/stream 失败不产生成功 `ModelResponse(status=...)`；失败通过 `ModelError` 或 `response_failed` 流事件表达，并由后续 runtime 构造 `ModelInvocationFailed`。

合法组合必须受 contract 校验约束：

| `ModelResponse.status` | 允许的 `stop_reason` | Runtime 判断 |
|---|---|---|
| `completed` | `completed` | 返回自然完成内容 |
| `completed` | `tool_use` | 响应有效，但下一步进入工具调度 |
| `incomplete` | `max_tokens`、`content_filtered`、`unknown` | 结果不完整，由策略决定是否继续或终止 |
| `refused` | `refused` | 返回受控拒绝，不视为 transport 错误 |

以下组合为非法：`status=completed` 搭配 `refused`/`max_tokens`；`status=refused` 搭配 `tool_use`；任何成功 `ModelResponse` 搭配 `error`。

### Stop Reason 映射

| 标准化 stop reason | OpenAI Chat Completions | OpenAI Responses | 对应 `status` | 后续 runtime 语义 |
|---|---|---|---|---|
| `completed` | `stop` 且无拒绝输出 | 无工具意图的 completed response | `completed` | 模型 step 正常完成 |
| `tool_use` | `tool_calls` | 完成的 function-call output item | `completed` | 后续进入工具调度 |
| `max_tokens` | `length` | 与 max output tokens 相关的 incomplete reason | `incomplete` | 响应被截断 |
| `content_filtered` | `content_filter` | provider 给出的 filter/policy incomplete reason | `incomplete` | 受控终止或策略处理 |
| `refused` | 可识别的 refusal 输出 | refusal output | `refused` | 有效的受控拒绝结果 |
| `unknown` | 新增未识别值 | 新增未识别值 | `incomplete` | 保留原值并保守处理 |

标准化不会丢弃 provider 信息：若 provider 提供原始停止原因，则写入 `provider_stop_reason`，供后续策略、日志或排障使用。

### RuntimeEvent 与模型生命周期 payload

```text
RuntimeEvent[Payload]
  event_id
  event_type
  event_version
  agent_run_id?
  step_id?
  session_id?
  trace_id
  span_id
  parent_span_id?
  actor_type
  actor_id?
  payload: typed payload
  created_at
```

本次定义的 durable model lifecycle events：

| 事件类型 | Payload 核心字段 |
|---|---|
| `ModelInvocationStarted` | `invocation_id`、`provider`、`model`、`protocol`、`profile`、`streaming` |
| `ModelInvocationCompleted` | `invocation_id`、`status`、`stop_reason`、`provider_stop_reason`、`usage`、`latency_ms`、`tool_call_count` |
| `ModelInvocationFailed` | `invocation_id`、错误分类、`retryable`、`fallback_allowed`、provider code/status、`latency_ms` |
| `ModelToolCallsProduced` | `invocation_id`、call identifiers、tool names、参数校验状态 |

`ModelStreamEvent` 与 `RuntimeEvent` 的边界如下：

```text
ModelStreamEvent
  高频、实时、供 stream consumer/reducer 使用
  例如 text delta、tool argument delta

RuntimeEvent
  低频、事实化、供后续持久化/审计/回放使用
  例如模型开始、模型完成、模型失败、产出工具意图
```

本变更只定义以上 schema，不创建数据库表、repository 或事件写入服务。

## 技术决策（Decisions）

### 1. 使用 ModelProfile 选择协议，而不是由 Provider 隐含协议

provider registration 只拥有 endpoint、auth 与 provider 配置；model profile 选择具体 protocol、capabilities 与受控参数/转换规则。

选择原因：

- 同一 provider 下不同模型可以具有不同调用规则。
- 非 OpenAI provider 后续可明确复用 `openai_chat`，而不是复制整套 adapter。
- capability 校验可在 transport 前完成。

备选方案：每个 provider 一个大 adapter，在内部按模型写条件判断。未采用，因为协议复用、模型差异与测试边界会纠缠在一起。

### 2. OpenAI Chat Completions 与 OpenAI Responses 作为独立协议实现

本次同时实现 `openai_chat` 和 `openai_responses`，两者共享公开 contracts、transport 与 reducer，但各自拥有请求编码、响应解析和 stream event 映射。

选择原因：

- 两者 wire payload 与 streaming event 结构不同。
- tool call、stop status 与 usage 的读取方式不同。
- 将两者模糊归为“OpenAI-compatible”会把协议判断泄漏到 parser 和 runtime。

备选方案：只实现 Chat，后续再增加 Responses。未采用，因为已确认两条协议均为本次实现范围。

### 3. Anthropic 只预留协议边界，不声明调用能力

`anthropic_messages` 作为可识别的协议身份和未来扩展边界存在，但本变更不要求 Anthropic endpoint、credentials、请求转换或响应解析通过远程调用验收。

选择原因：能够提前固定 provider/protocol 分离的架构，而不扩大当前真实远程 provider 交付范围。

备选方案：本次直接实现 Anthropic。未采用，因为用户已确认只需要预留 protocol。

### 4. `custom` 只提供可注册抽象，不提供内置可执行实现

`custom.py` 定义符合 `ProtocolAdapter` 的抽象扩展边界；第三方 provider 必须显式注册具体 adapter 才能让 custom profile 可执行。本次没有任何内置 custom transport 或任意 hook 执行器。

选择原因：提前固定自定义协议如何接入统一 response/error/stream contract，同时避免提供无法治理的动态回调面。

### 5. Timeout 属于 ModelRequest 的调用控制字段

`timeout_seconds` 由单次 `ModelRequest` 可选指定，未指定时使用 provider/transport 默认值；它不属于改变模型生成行为的 `ModelOptions`。

选择原因：不同 agent run 或 step 可能需要不同调用时限，且 `ModelTimeoutError` 必须能与具体 invocation 对应；同时不应把 transport 控制参数混入 provider generation options。

备选方案：仅使用全局/transport timeout。未采用，因为无法让调用方为单次 agent step 施加明确上限。

### 6. Streaming 归约为与 Blocking 一致的最终响应

streaming 路径先输出类型化 delta events，再由 reducer 组合为最终 `ModelResponse`。runtime 后续只需对统一 response 的 tool、stop 和 usage 语义进行判断。

备选方案：把 provider 原始 SSE 直接向上层暴露。未采用，因为这会将 OpenAI Chat/Responses 的差异传播到 runtime。

### 7. `src/exceptions` 直接成为正式入口

平台异常从 `src/core/errors.py` 迁移到 `src/exceptions`，现有使用方直接调整导入，不保留过渡 re-export。

选择原因：在模型错误体系加入前就确定统一所有权，避免长期存在两套公共异常入口。

备选方案：保留 core 异常并仅新增 `models/errors.py`。未采用，因为 models 专属错误仍需要继承平台级正式基类。

### 8. Events 只定义事实契约，不建设事件基础设施

模型能力需要说明将产生哪些事实，但本次无需写入或查询事件。Event Store、bus 与 replay 需要 runtime/storage 设计配合，不能附带在 adapter 实现中。

### 9. 本次排除 pricing、budget 与自动 retry

adapter 报告一次调用的 usage，并通过 `ModelError` 提供 `retryable` 等决策字段；预算、成本和重试执行由后续 runtime/observability 能力承担。

选择原因：这些行为需要 agent run 级上下文、幂等策略及事件持久化，而当前变更只建立调用边界。

## 错误处理策略

- 公开 `ModelRequest` 在外部调用前完成 schema 验证；模型不支持的能力或选项在 selector/profile 校验阶段失败。
- provider 的鉴权、授权、限流、超时、不可用和错误响应由 protocol/error parser 映射到 `ModelError` 子类。
- malformed response、非法 tool arguments 或无法归一化的流事件转为 `ModelResponseParseError`。
- stream 在已经输出部分内容后失败时，转为 `ModelStreamInterruptedError`，使后续 runtime 能识别其与“请求尚未开始即失败”的区别。
- `refused` 与 `tool_use` 属于有效响应分支，不转换为 transport/protocol 异常。
- transport 按 `InvocationContext.effective_timeout_seconds` 执行调用级 timeout；超时映射为模型超时或带部分输出的流中断错误。
- models 不执行自动 retry 或 fallback；后续 runtime 依据标准错误字段作出策略决策。

## 安全设计

- `transport/auth.py` 是唯一允许物化 provider credentials 与 auth headers 的模型组件。
- contracts、标准化异常及模型事件 payload 不包含 API key、authorization header 或其他 secret。
- lifecycle event 仅要求记录调用标识、provider/model/protocol、usage、stop reason、错误分类、时延和工具名称等最小审计字段。
- 事件不要求保存完整 prompt、完整模型返回文本、raw wire body 或未脱敏工具 arguments。
- Mock provider 可在无外部凭证、无网络条件下覆盖文本、工具和失败测试。
- models 产出的工具调用只是 intent；工具授权、审批、sandbox 与执行仍属于未来 runtime/tools 能力。

## 与现有模块的集成及替代关系

| 模块 | 本变更影响 |
|---|---|
| `src/api` | `BaseError` 等导入迁移至 `src.exceptions`；不新增模型 API |
| `src/core` | 不再拥有异常定义；仍拥有配置、日志、context 与通用工具 |
| `src/contracts/database` | 承载既有 ORM 基础模型与数据库类型，不混入 runtime payload |
| `src/contracts/runtime` | 新增模型与事件的全部跨模块 schema |
| `src/models` | 新增 adapter、selector/profile、协议、transport、parser 与 reducer |
| `src/events` | 仅提供事件 contract/type 的发现入口；无持久化实现 |
| 后续 `src/runtime` | 消费 `ModelResponse`、`ModelStreamEvent` 与 `ModelError`，并根据 contracts 构造事实事件 |
| 后续 `src/observability` | 基于模型 usage 与 lifecycle payload 聚合 metrics/cost |

## 最小实现路径

本变更的最小可用实施顺序为：

1. 建立 `src/exceptions` 并迁移当前平台异常引用。
2. 定义稳定的模型与事件 contracts，并用 schema 测试固定公开边界。
3. 实现 provider/protocol/profile 注册与 capability 校验。
4. 实现 Mock provider，覆盖 blocking、streaming、tool 与错误路径。
5. 实现 OpenAI Chat Completions 的 blocking/streaming 路径。
6. 实现 OpenAI Responses 的 blocking/streaming 路径。
7. 实现 stream reducer、错误映射和事件 payload 互操作测试。
8. 更新架构说明，记录 reserved Anthropic 与非目标边界。

这一顺序不引入数据库迁移、runtime 编排或未要求的 provider 调用，但可为下一阶段 runtime/tool-loop 提供完整稳定的输入输出面。

## 迁移方案（Migration Plan）

1. 新增 `src/exceptions`，把现有通用异常定义迁移到新的正式入口，并增加 model 专属错误。
2. 更新 API、鉴权、core 导出及测试中的异常引用；确认代码库无 `src.core.errors` 引用后移除旧模块。
3. 新增 `src/contracts` 模型/事件 schema 与单元测试。
4. 新增 models 选择、协议和 Mock 实现，使用 fake transport/SSE fixture 完成无网络验证。
5. 新增 OpenAI Chat 与 Responses 两类协议实现及完整测试。
6. 验证模型结果和错误可构造事件 payload；不执行数据库 migration。
7. 更新相关文档，明确调用支持范围与未来 runtime 的消费边界。

回滚策略为代码回退：恢复旧异常导入，移除新增 contracts/models/events 文件及相关配置。由于本变更没有数据库 schema 或远程资源变更，不涉及数据回滚。

## 风险与权衡（Risks / Trade-offs）

- [风险] 同期实现两类 OpenAI protocol 与 streaming，会增加首次实现规模。  
  -> 缓解：仅共享公开 contract、HTTP transport 与 reducer；wire parser 分开实现并分别测试。
- [风险] `anthropic_messages` 预留模块可能被误认为已支持 Anthropic 调用。  
  -> 缓解：spec 明确要求未实现 provider 时调用失败，测试断言不发生网络请求。
- [风险] 删除 `src.core.errors` 可能遗漏内部 import，造成运行时导入失败。  
  -> 缓解：将全仓检索无旧入口引用和现有测试通过写入任务验收。
- [风险] 不同协议对 token usage 的定义不完全一致，过度归一化会丢失诊断信息。  
  -> 缓解：标准字段允许空值，并保留经过安全筛选的 `provider_details`。
- [风险] 后续消费者可能把敏感模型内容写入通用事件 payload。  
  -> 缓解：本次定义的 typed model payload 不要求 raw content，并明确事件安全边界。

## 待确认问题（Open Questions）

- 实现阶段需根据首批配置模型决定默认 profile 使用 `openai_chat` 还是 `openai_responses`；测试与显式请求可以固定 protocol 以保持确定性。
- 后续 API 若需要对客户端提供 streaming，应决定是否直接暴露标准化 `ModelStreamEvent`，或再映射为 API 专属 SSE schema；该决策不属于本变更。
