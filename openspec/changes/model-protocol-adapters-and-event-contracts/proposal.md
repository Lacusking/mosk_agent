## Why

Agent runtime 需要面对同一 provider 下模型协议差异、OpenAI 两类接口差异、流式工具调用与错误分级处理；当前仓库仅有基础异常与模块骨架，缺少可供 runtime 依赖的统一模型及事件契约。现在先固定 adapter、异常和事件边界，可避免后续 tool loop、观测与 provider 扩展重复重构。

## What Changes

- 新增统一模型调用契约，覆盖 blocking/streaming、tool call、stop reason 与 token usage 分段信息。
- 新增模型适配层：实现 OpenAI Chat Completions、OpenAI Responses 与 Mock；预留 Anthropic Messages/custom protocol 扩展接口，不调用 Anthropic 服务。
- 新增模型生命周期事件定义，供后续 runtime/Event Store 消费；本次不实现事件持久化。
- **BREAKING**：新增正式平台异常入口 `src/exceptions`，迁移当前 `src.core.errors` 的使用方，并提供 models 专属、可供 runtime 判定的错误类型。
- 将 streaming 作为本次交付范围：虽原规划为增强项，但它直接决定 tool call、usage 与事件 contracts 的正确形状。

## Capabilities

### New Capabilities
- `platform-exceptions-foundation`: 定义平台正式异常包及 models 专属可判定错误语义。
- `model-invocation-contracts`: 定义模型消息、调用结果、流式事件、工具调用、stop reason 与 usage 契约。
- `openai-protocol-adapters`: 定义 provider/profile/protocol 分层，并实现 OpenAI Chat、OpenAI Responses、Mock 的 blocking 与 streaming 行为。
- `model-runtime-event-contracts`: 定义模型调用、工具意图和失败事实的 RuntimeEvent 类型与 payload。

### Modified Capabilities

- 无。

## Impact

- 受影响模块：`src/exceptions`、`src/core`、`src/api`、`src/contracts`、`src/models`、`src/events`、`tests`、`docs`。
- API 兼容性影响：本次不新增 HTTP endpoint；内部 import 从 `src.core.errors` 切换为 `src.exceptions`，属于内部破坏性变更。
- 配置风险：新增 OpenAI provider、模型 profile 与协议选择配置；未配置真实凭证时必须可使用 Mock 验收。
- 数据迁移风险：无。本次仅定义 RuntimeEvent 契约，不建立 Event Store 表或 migration。
- 关键假设：MVP 的真实远程 provider 仍为 OpenAI；Anthropic 仅保留协议扩展边界；runtime 与工具执行消费这些契约但不在本变更实现。
- 歧义取舍：OpenAI Chat 与 Responses 都进入实现范围；provider 与 protocol 独立建模，以覆盖 OpenAI-compatible 或自定义厂商协议。
- 最小改动理由：只实现模型调用与所必需的公共契约、异常迁移和事件定义，不引入 pricing、budget、自动重试、事件存储或 Anthropic 网络调用。

## Non-goals

- 不实现 Anthropic、Gemini、Ollama 或其他第三方 provider 的远程调用。
- 不实现 Event Store、Event Bus、replay、runtime tool dispatch 或任务聚合统计。
- 不实现成本定价、预算拦截、自动 fallback 或生产级重试策略。
