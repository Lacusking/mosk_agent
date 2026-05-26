## 1. 平台异常入口迁移（src/exceptions, src/core, src/api, testing）

- [x] 1.1 [platform-exceptions-foundation][src/exceptions] 建立 `BaseError`、公共异常与 `ModelError` 专属层级，包含 provider/model/operation、retryable、fallback 与 provider 诊断字段；验证：`pytest -q tests/exceptions` 覆盖公共序列化和模型错误分类。
- [x] 1.2 [platform-exceptions-foundation][src/api, src/core] 将 API exception handler、鉴权依赖与 core 对异常的导入迁移到 `src.exceptions`，移除 `src.core.errors` 公共入口；验证：`rg "src\\.core\\.errors" src tests` 无应用依赖且 `pytest -q tests/core tests/api` 通过。
- [x] 1.3 [platform-exceptions-foundation][testing] 增加模型错误安全与判定字段测试，覆盖限流/超时可重试、认证/能力错误不可重试及敏感凭证不出现在公开数据中；验证：`pytest -q tests/exceptions -k model` 通过。

## 2. 模型与事件公开契约（src/contracts/runtime, testing）

- [x] 2.1 [model-invocation-contracts][src/contracts/runtime] 定义模型消息/content blocks、工具声明与工具调用、能力、生成选项、带调用级 `timeout_seconds` 的 `ModelRequest`、`ModelResponse` 及 status/stop reason 合法映射；验证：`pytest -q tests/contracts -k model` 覆盖合法序列化、非法 timeout 和非法状态组合拒绝。
- [x] 2.2 [model-invocation-contracts][src/contracts/runtime] 定义 `ModelUsage` 阶段细分与 `ModelStreamEvent` typed payload，明确缺失 token 值不伪造为零；验证：`pytest -q tests/contracts -k "usage or stream"` 通过。
- [x] 2.3 [model-runtime-event-contracts][src/contracts/runtime, src/events] 定义 `RuntimeEvent` envelope、模型生命周期事件枚举及 Started/Completed/Failed/ToolCallsProduced typed payload，并提供 `src.events` 可发现导出；验证：`pytest -q tests/contracts -k event` 验证事件序列化和非法 payload 拒绝。
- [x] 2.4 [model-runtime-event-contracts][testing] 增加事件敏感数据边界测试，确保 model lifecycle payload 无需 raw request/response、完整 prompt 或完整工具参数即可构造；验证：`pytest -q tests/contracts -k event_security` 通过。

## 3. Adapter 基础与模型选择（src/models, src/core, testing）

- [ ] 3.1 [openai-protocol-adapters][src/models] 建立 adapter/protocol 接口、`InvocationContext`、provider registry、model profiles 与 capabilities 校验，确保 provider、protocol、model profile 可独立组合且上下文不含敏感正文；验证：`pytest -q tests/models -k "registry or selector or profile or context"` 覆盖同 provider 多 profile、不支持能力拒绝及安全 context。
- [ ] 3.2 [openai-protocol-adapters][src/core, src/models] 增加 OpenAI/Mock 必需配置和 transport/auth 边界，使用现有 `httpx` 封装认证头、请求路径及 provider 默认/request 覆盖 timeout 且不暴露 secret；验证：`pytest -q tests/models -k "config or transport or auth or timeout"` 通过。
- [ ] 3.3 [openai-protocol-adapters][src/models] 注册 `anthropic_messages` 协议身份并定义 `CustomProtocolAdapter` 抽象注册边界；对未实现/未注册协议调用明确返回模型能力/配置错误；验证：`pytest -q tests/models -k "anthropic or custom or reserved"` 通过且测试断言未发生网络调用或任意 hook 执行。
- [ ] 3.4 [openai-protocol-adapters][src/models] 实现 Mock blocking/streaming 响应、工具意图与可配置失败路径，为无凭证测试提供确定性行为；验证：`pytest -q tests/models -k mock` 通过。

## 4. OpenAI Chat Completions 协议（src/models, testing）

- [ ] 4.1 [openai-protocol-adapters][src/models] 实现 `openai_chat` blocking 请求转换及文本/tool call/stop reason/usage 响应解析；验证：使用 fake HTTP responses 执行 `pytest -q tests/models -k "openai_chat and blocking"`。
- [ ] 4.2 [openai-protocol-adapters][src/models] 实现 `openai_chat` SSE/chunk 转换与工具 argument 片段处理，输出统一 stream events；验证：`pytest -q tests/models -k "openai_chat and streaming"` 覆盖文本、工具片段及完成原因。
- [ ] 4.3 [model-invocation-contracts][src/models, testing] 实现 stream reducer 的 Chat 路径验收，验证未完成工具 JSON 不可成为完成调用、完成 stream 与 blocking 最终语义同构；验证：`pytest -q tests/models -k "openai_chat and reducer"`。

## 5. OpenAI Responses 协议（src/models, testing）

- [ ] 5.1 [openai-protocol-adapters][src/models] 实现 `openai_responses` blocking 请求转换及 output text/function call/refusal/incomplete/usage 解析；验证：使用 fake HTTP responses 执行 `pytest -q tests/models -k "openai_responses and blocking"`。
- [ ] 5.2 [openai-protocol-adapters][src/models] 实现 Responses 语义化 stream events 到统一 `ModelStreamEvent` 的转换，覆盖 output text delta、function arguments delta/done、completed 与 failed；验证：`pytest -q tests/models -k "openai_responses and streaming"`。
- [ ] 5.3 [model-invocation-contracts][src/models, testing] 实现 stream reducer 的 Responses 路径验收，验证 tool/stop/usage 归约结果与统一响应契约一致；验证：`pytest -q tests/models -k "openai_responses and reducer"`。

## 6. 错误映射、事件互操作与安全测试（src/models, testing）

- [ ] 6.1 [platform-exceptions-foundation][src/models] 实现协议错误 parser，将 OpenAI blocking/streaming 的认证、权限、限流、超时、服务不可用、非法请求及流中断映射为 `ModelError` 类型；验证：`pytest -q tests/models -k error` 覆盖各决策字段。
- [ ] 6.2 [model-runtime-event-contracts][testing] 基于 Mock/OpenAI 统一响应和模型错误构造四种 lifecycle event payload，验证 tool use 是成功事件且失败事件携带 retry 语义；验证：`pytest -q tests/models tests/contracts -k lifecycle`。
- [ ] 6.3 [platform-exceptions-foundation][model-runtime-event-contracts][testing] 增加安全回归测试，验证日志/错误/event 结构不含 API key、authorization header、raw wire body 或未脱敏完整工具参数；验证：`pytest -q tests/models tests/contracts tests/exceptions -k security`。

## 7. 集成验收与文档（testing, docs）

- [ ] 7.1 [openai-protocol-adapters][testing] 增加无外部网络的 adapter 集成测试，覆盖 Mock、OpenAI Chat 和 Responses 的 blocking/streaming 文本与工具流程；验证：`pytest -q tests/models tests/contracts tests/exceptions` 全通过。
- [ ] 7.2 [model-invocation-contracts][platform-exceptions-foundation][testing] 执行质量校验并修复 typing/lint 问题，确认迁移后当前测试不回归；验证：`ruff check src tests && pytest -q`。
- [x] 7.3 [model-runtime-event-contracts][docs] 更新架构说明，记录正式 exceptions 入口、provider/protocol/profile 边界、OpenAI 两种协议、Anthropic reserved 状态、stream event 与 durable event 的分界；验证：文档明确列出本变更非目标（无 Event Store、无 Anthropic 调用、无 pricing/budget/retry）。
