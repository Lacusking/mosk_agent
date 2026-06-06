## 1. 上下文契约与配置（src/context, src/core）

- [x] 1.1 [01-context-assembly-budgeting][src/context] 创建 `src/context` 模块结构，定义 ContextItem、ContextBundle、ContextBudget、source/type 枚举与安全 metadata 校验；验证：`pytest -q tests/context -k "schemas or metadata"`。
- [x] 1.2 [01-context-assembly-budgeting][src/context] 实现 ContextBundle 对 session message items 的模型消息视图转换，保持 sequence 升序；验证：`pytest -q tests/context -k "bundle or model_messages"`。
- [x] 1.3 [01-context-assembly-budgeting][src/core] 增加 context window 与 snip 的保守默认配置及校验；验证：`pytest -q tests/core -k context`。

## 2. Builder 与 Pipeline（src/context）

- [x] 2.1 [01-context-assembly-budgeting][src/context] 实现 ContextBuilder，通过 `context_message_sequence` 读取 AgentRun 的 session 历史并构造 session message ContextItem；验证：`pytest -q tests/context -k builder`。
- [x] 2.2 [01-context-assembly-budgeting][src/context] 定义 ContextStrategy 协议与 ContextStrategyPipeline，支持策略有序执行与失败传播；验证：`pytest -q tests/context -k pipeline`。
- [x] 2.3 [01-context-assembly-budgeting][src/context] 实现 window 读取行为作为 builder 读取参数：按水位内最近 N 条消息限制查询范围，保持 sequence 升序；验证：`pytest -q tests/context -k window`。
- [x] 2.4 [01-context-assembly-budgeting][src/context] 新增预留策略模块（microCompact、toolResultBudget、autoCompact、reactiveCompact），包含完整类定义、docstring 与 `NotImplementedError` 方法体，不接入默认 pipeline；验证：`pytest -q tests/context -k reserved`。

## 3. Snip Compact（src/context）

- [x] 3.1 [01-context-assembly-budgeting][src/context] 实现 snipCompact 策略，对超阈值 session message items 保留 pinned/不可驱逐/高优先级/头部/尾部 items，裁剪中间可驱逐内容；验证：`pytest -q tests/context -k snip_compact`。
- [x] 3.2 [01-context-assembly-budgeting][src/context] 增加短上下文不裁剪、无可驱逐 items、非法阈值与空可见用户上下文等边界与失败场景测试；验证：`pytest -q tests/context -k "snip_compact or error"`。

## 4. Runtime 集成（src/runtime）

- [x] 4.1 [01-context-assembly-budgeting][src/runtime] 删除 `src/runtime/context.py`（`RuntimeContextBuilder`），将新 ContextBuilder 注入 AgentRuntimeKernel，替换 kernel 中对 `SessionManager.model_context()` 与旧 `RuntimeContextBuilder` 的引用；验证：`pytest -q tests/runtime -k "kernel or context"`。
- [x] 4.2 [01-context-assembly-budgeting][src/runtime] 确认现有 pattern 仍通过 `PatternRuntimeState.visible_context_messages` 消费上下文，不需要感知 ContextBundle；验证：`pytest -q tests/runtime -k "kernel or pattern"`。
- [x] 4.3 [01-context-assembly-budgeting][src/runtime] 保持 ReAct observation 归属不变：工具结果留在 `PatternRuntimeState.observations`，不复制到 ContextBundle.tool_observations；验证：`pytest -q tests/runtime -k "react or observation"`。

## 5. 集成验收、文档与质量（testing, docs）

- [x] 5.1 [01-context-assembly-budgeting][testing] 增加多轮会话历史、AgentRun 水位隔离、context window 与最终 assistant 消息提交不变的集成测试覆盖；验证：`pytest -q tests/integration -k "context or agent_run"`。
- [x] 5.2 [01-context-assembly-budgeting][docs] 更新架构/结构文档，标注 `src/context` 为上下文装配与 token budget 入口；验证：人工检查文档中 runtime/session 上下文流的引用。
- [x] 5.3 [01-context-assembly-budgeting][testing] 执行受影响模块的质量检查并修复回归；验证：`ruff check src tests && pytest -q tests/context tests/runtime tests/patterns`。

## 6. Token 计数与预算（src/context, src/models, src/core）

- [ ] 6.1 [02-token-budget-and-counting][src/context] 定义 `TokenCounter` 协议与 `DefaultTokenCounter`（字符长度估算），实现 `count`/`count_message`/`count_messages` 方法；验证：`pytest -q tests/context -k token_counter`。
- [ ] 6.2 [02-token-budget-and-counting][src/context] 可选实现 `TiktokenCounter` 适配器，依赖 tiktoken 包时启用；验证：`pytest -q tests/context -k tiktoken`。
- [ ] 6.3 [02-token-budget-and-counting][src/models] 为 `ModelProfile` 增加 `context_window_tokens: int | None` 字段，不破坏现有 profile 注册；验证：`pytest -q tests/models -k profile`。
- [ ] 6.4 [02-token-budget-and-counting][src/context] 在 ContextBuilder 中实现预飞行 token 校验：装配后计算 token 总量，与 profile context window 或全局默认预算比较；超预算时触发 token 级裁剪；验证：`pytest -q tests/context -k "preflight or token_budget"`。
- [ ] 6.5 [02-token-budget-and-counting][src/core] 增加 `CONTEXT_TOKEN_BUDGET`、`CONTEXT_TOKEN_RESERVE` 配置项及校验；验证：`pytest -q tests/core -k "token or context"`。

## 7. 进阶压缩策略（src/context）

- [ ] 7.1 [03-advanced-compact-strategies][src/context] 实现 microCompact 策略：截断超过 token 上限的单个 ContextItem 内容，保留首尾片段；验证：`pytest -q tests/context -k micro_compact`。
- [ ] 7.2 [03-advanced-compact-strategies][src/context] 实现 toolResultBudget 策略：限制 tool observation items 的 token 总量，超出时按优先级和时间裁剪；验证：`pytest -q tests/context -k tool_result_budget`。
- [ ] 7.3 [03-advanced-compact-strategies][src/context] 实现 autoCompact 策略：调用 LLM 将被驱逐内容压缩为临时摘要 ContextItem，失败时回退到无摘要裁剪；验证：`pytest -q tests/context -k auto_compact`。
- [ ] 7.4 [03-advanced-compact-strategies][src/context] 将 microCompact 和 toolResultBudget 接入默认 pipeline，autoCompact 默认关闭；验证：`pytest -q tests/context -k "pipeline and compact"`。

## 8. Observation 上下文装配（src/context, src/runtime）

- [ ] 8.1 [04-observation-context-assembly][src/context] 在 ContextBuilder 中实现从 PatternRuntimeState.observations 提取已完成 tool_result，转换为 ContextItem 并装配到 ContextBundle.tool_observations；验证：`pytest -q tests/context -k observation`。
- [ ] 8.2 [04-observation-context-assembly][src/context] 实现以 call_id 为标识的去重逻辑，避免同一 observation 在模型消息中重复出现；验证：`pytest -q tests/context -k "observation and dedup"`。
- [ ] 8.3 [04-observation-context-assembly][src/runtime] 确认 pattern 仍从 PatternRuntimeState.observations 读取动作决策信息，不依赖 ContextBundle；验证：`pytest -q tests/runtime -k "react or observation"`。

## 9. 响应式上下文恢复（src/exceptions, src/models, src/runtime）

- [ ] 9.1 [05-reactive-context-recovery][src/exceptions] 新增 `ModelContextLengthError` 异常类型，标记 `retryable=True`，携带 `provider_reported_tokens` 字段；验证：`pytest -q tests/exceptions -k context_length`。
- [ ] 9.2 [05-reactive-context-recovery][src/models] 在 OpenAI error parser 中将 413/context_length_exceeded 映射为 `ModelContextLengthError`；验证：`pytest -q tests/models -k "context_length or error"`。
- [ ] 9.3 [05-reactive-context-recovery][src/runtime] 在 `decide_model_error()` 中增加 `ModelContextLengthError` 识别分支，返回 `context_reduction_retry` 决策；验证：`pytest -q tests/runtime -k "error_policy and context"`。
- [ ] 9.4 [05-reactive-context-recovery][src/runtime] 在 kernel `_call_model()` 中实现渐进缩减重试：降低 snip 阈值 + 启用 microCompact，最多一次缩减重试；验证：`pytest -q tests/runtime -k "context_reduction or reactive"`。

## 10. 扩展验收与质量（testing, docs）

- [ ] 10.1 [02-05][testing] 增加 token 预算、压缩策略、observation 装配与响应式恢复的集成测试覆盖；验证：`pytest -q tests/integration -k "token or compact or observation or context_recovery"`。
- [ ] 10.2 [02-05][docs] 更新架构/结构文档，说明 TokenCounter、压缩策略链、observation 装配边界与响应式恢复流程；验证：人工检查文档一致性。
- [ ] 10.3 [02-05][testing] 执行全量质量检查；验证：`ruff check src tests && pytest -q`。
