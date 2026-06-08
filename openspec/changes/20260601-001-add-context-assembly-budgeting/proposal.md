---
created: 2026-06-01
status: active
source: P0 上下文与记忆层 — context 装配与 token budget（project.md §8.1）
---

## Why

Agent runtime session 与 pattern 主链路已基本具备，但当前上下文仍由 runtime 直接读取 session history 并转换为 model messages，缺少统一的上下文装配、预算和裁剪边界。现在引入独立 context 能力，可以在不改动后续 Runtime 主链路的前提下，逐步承载 window context、ContextItem/ContextBundle、策略 pipeline，以及未来 memory、tool observation、artifact 和压缩策略。

## What Changes

- 新增 `ContextItem` 结构，将会话消息、摘要、工具观察、artifact/RAG 片段等上下文来源包装为统一 item，包含 source/type/content/priority/token_count/pinned/evictable 等裁剪所需元数据。
- 新增 `ContextBundle` 作为 ContextBuilder 输出，显式划分 session messages、memory summary、tool observations、artifacts 等槽位。
- 新增 ContextBuilder / ContextStrategy / ContextStrategyPipeline 边界，删除 `src/runtime/context.py`（`RuntimeContextBuilder`），runtime 不再直接从 SessionManager 读取 `list[ModelMessage]`，而是通过 context 能力得到可交给 pattern 的可见上下文。
- 实现 window context：按 AgentRun 固定的 `context_message_sequence` 与最近 N 条 session messages 读取用户可见历史，保持 sequence 升序进入模型上下文。
- 实现 `snipCompact` 策略：按消息数阈值裁剪中间可驱逐内容，保留 pinned/高优先级/头部/尾部 item。
- 实现 `TokenCounter` 协议与 token 级预算校验：为 `ModelProfile` 增加 `context_window_tokens`，在模型调用前校验上下文 token 总量。
- 实现 `microCompact`（截断过长单项）、`toolResultBudget`（限制工具结果总 token 量）、`autoCompact`（LLM 临时摘要，不持久化为 Summary Memory）三种进阶压缩策略。
- 将 ReAct 已完成的 tool observation 装配到 ContextBundle.tool_observations，使模型在后续 step 中可引用之前工具结果；保持 PatternRuntimeState.observations 作为 pattern 动作决策输入。
- Artifact 装配与 RAG 检索不在本期范围，`ContextBundle.artifacts` 槽位保留但不填充。
- 新增 `ModelContextLengthError` 异常类型，实现 prompt_too_long/413 的响应式恢复：渐进缩减上下文后重试，失败则终止 run。

## Capabilities

### New Capabilities

- `01-context-assembly-budgeting`：上下文 item/bundle 契约、构建入口、策略管线、session window 装配和 snipCompact。
- `02-token-budget-and-counting`：TokenCounter 协议、ModelProfile context window、token 级预飞行校验与 token 级裁剪。
- `03-advanced-compact-strategies`：microCompact 截断、toolResultBudget 限额、autoCompact LLM 临时摘要。
- `04-observation-context-assembly`：ReAct tool observation 装配到 ContextBundle，observation 生命周期边界。
- `05-reactive-context-recovery`：ModelContextLengthError 异常、error_policy 上下文超限分支、渐进缩减重试。

### Modified Capabilities

- 无。本变更通过新增 context capability 接入已实现的 AgentRun runtime，不修改既有公开 API 行为。

## Impact

- 受影响模块：`src/contracts`、`src/context`、`src/runtime`、`src/sessions`、`src/patterns`、`src/models`、`src/tools`、`src/exceptions`、`src/core`、`tests`、`docs`。
- API 兼容性：不新增或修改 REST/SSE API；上下文装配属于服务内部主链路变化，对外响应语义保持不变。
- 配置风险：新增 session window、snip threshold、token budget、microCompact 上限、toolResultBudget 上限、autoCompact 开关等配置；默认值必须保守。
- 数据迁移风险：无数据库 migration。只读取现有表，不新增表、不修改存储 schema。
- 关键假设与取舍：token 计数首期以字符长度估算为默认，可选配精确 tokenizer；autoCompact 的 LLM 调用使用当前 run 的模型配置；artifact 装配与 RAG 检索留给后续 change。
- 最小改动理由：把 runtime 对上下文的依赖收敛到 `ContextBuilder -> ContextBundle -> Pipeline`，一次建立完整的 token 预算、压缩、装配和错误恢复边界。

## Non-goals

- 不实现 Summary Memory 的创建、更新或持久化写入（autoCompact 的临时摘要仅用于当前 run，不等同于 Summary Memory）。
- 不实现 Artifact 装配协议、加载器或 mock 实现。
- 不实现 RAG 检索协议、检索引擎或相关装配逻辑。
- 不改变当前 AgentRun/Session/Pattern 的公开 REST/SSE API 契约。
- 不新增数据库 migration。
- 不实现成本计费或自动模型 fallback。
