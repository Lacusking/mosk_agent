## Architecture

### 背景

`agent-runtime-sessions-patterns` 已建立 Session、AgentRun、Pattern、Runtime kernel 与可见消息历史，但当前模型上下文仍由 runtime 直接调用 SessionManager 读取并转换为 `list[ModelMessage]`。这能支撑短会话，但无法承载 P0 规划中的 context/token budget，也会让后续 Summary Memory、tool observation、artifact/RAG 接入时反复修改 kernel 与 pattern 主链路。

当前相关状态：

```text
AgentRuntimeKernel
  -> SessionManager.model_context(session_id, context_message_sequence)
  -> list[ModelMessage]
  -> PatternRuntimeState.visible_context_messages
  -> Pattern.next_action()
```

目标状态：

```text
AgentRuntimeKernel
  -> ContextBuilder.build(agent_run)
  -> ContextBundle
  -> ContextStrategyPipeline.apply(bundle)
  -> PatternRuntimeState.visible_context_messages
  -> Pattern.next_action()
```

本设计只处理 context 装配与预算边界，不改变外部 API，不新增数据库表。

### Goals / Non-Goals

**Goals:**

- 建立 `src/context` 作为上下文与记忆层的 P0 能力入口。
- 定义 `ContextItem`、`ContextBundle`、`ContextBuilder`、`ContextStrategy` 与 `ContextStrategyPipeline`。
- 让 runtime 通过 context builder 获取可见上下文，不再直接依赖 SessionManager 的 model context 细节。
- 实现 session message window：读取 AgentRun 水位内最近 N 条消息，按 sequence 升序进入模型调用。
- 实现 `snipCompact`：按消息数阈值裁剪中间可驱逐内容。
- 实现 `TokenCounter` 协议与 token 级预算校验，为 `ModelProfile` 增加 `context_window_tokens`。
- 实现 `microCompact`（截断过长单项）、`toolResultBudget`（限制工具结果总 token）、`autoCompact`（LLM 临时摘要，不持久化）。
- 将 ReAct 已完成 tool observation 装配到 ContextBundle.tool_observations，保持 PatternRuntimeState.observations 作为 pattern 动作决策输入。
- Artifact 装配与 RAG 检索留给后续 change，`ContextBundle.artifacts` 槽位保留但本期不填充。
- 新增 `ModelContextLengthError`，实现 prompt_too_long/413 的渐进缩减重试。

**Non-Goals:**

- 不实现 Summary Memory 的创建、更新或持久化写入（autoCompact 临时摘要仅用于当前 run）。
- 不实现 Artifact 装配协议、加载器或 mock 实现。
- 不实现 RAG 检索协议、检索引擎或相关装配逻辑。
- 不改变当前 AgentRun/Session/Pattern 的公开 REST/SSE API 契约。
- 不新增数据库 migration。
- 不实现成本计费或自动模型 fallback。

### 上下文装配流

```text
                 ┌────────────────────┐
                 │      AgentRun      │
                 │ session_id/watermark│
                 └─────────┬──────────┘
                           │
                           ▼
                 ┌────────────────────┐
                 │   ContextBuilder   │
                 │  (window 读取参数)  │
                 └─────────┬──────────┘
                           │
       ┌───────────┬───────┼──────────┬──────────┐
       ▼           ▼       ▼          ▼          ▼
  session msgs  memory  tool obs  artifacts    RAG
  (implemented) (slot)  (04-impl) (reserved) (reserved)
       └───────────┴───────┬──────────┴──────────┘
                           ▼
                 ┌────────────────────┐
                 │   ContextBundle    │
                 │  + TokenCounter    │
                 └─────────┬──────────┘
                           ▼
                 ┌────────────────────┐
                 │ StrategyPipeline   │
                 │  snipCompact       │
                 │  microCompact      │
                 │  toolResultBudget  │
                 │  autoCompact       │
                 │  token 预飞行校验   │
                 └─────────┬──────────┘
                           ▼
              visible_context_messages
                           │
                           ▼ (if ModelContextLengthError)
                 ┌────────────────────┐
                 │  Reactive Recovery │
                 │  渐进缩减 + 重试    │
                 └────────────────────┘
```

### 目录

```text
src/context/
├── __init__.py
├── builder.py              # ContextBuilder：装配 + window 读取 + 预飞行 token 校验
├── schemas.py              # ContextItem / ContextBundle / ContextBudget / 枚举
├── budget.py               # TokenCounter 协议 + 默认估算 + 可选 tiktoken 适配
├── pipeline.py             # ContextStrategyPipeline
├── errors.py               # ContextBudgetError / ContextAssemblyError
└── strategies/
    ├── __init__.py
    ├── base.py             # ContextStrategy 协议
    ├── snip_compact.py     # 消息数裁剪（已实现）
    ├── micro_compact.py    # 单项截断
    ├── tool_result_budget.py  # 工具结果总量限制
    └── auto_compact.py     # LLM 临时摘要
```

Window 行为内置于 builder 读取逻辑，不需要独立策略文件。

`micro_compact.py`、`tool_result_budget.py`、`auto_compact.py`、`reactive_compact.py` 首期定义完整的策略类骨架（类定义、docstring、`apply()` 方法返回 `NotImplementedError`），不接入默认 pipeline。不创建只有 `pass` 或空内容的文件。

### 技术决策

#### Decision 1: ContextBuilder 返回 ContextBundle，而不是直接返回 ModelMessage

理由：`ModelMessage` 是模型调用格式，不足以表达 source、priority、pinned、evictable、token_count 等预算信息。`ContextBundle` 保留结构化槽位，最后一步再转换为 pattern 可消费的 `visible_context_messages`。

替代方案：继续让 SessionManager 返回 `list[ModelMessage]`，在 runtime 中裁剪。该方案改动最小，但会把上下文策略写进 kernel，后续 memory/RAG/artifact 接入会扩大 runtime 职责。

#### Decision 2: ContextItem.content 使用明确联合类型

`ContextItem.content` 定义为 `ModelMessage | dict[str, JsonValue]` 联合类型：

- `ModelMessage`：session message item 在 builder 构造时即完成从 SessionMessage 到 ModelMessage 的转换并存入 content，`to_model_messages()` 只做提取不做转换。
- `dict[str, JsonValue]`：后续 memory summary、tool observation、artifact 等来源使用安全 JSON 表达，进入模型前需要各自的转换器。

每种 `source` 应定义 content 校验规则。首期只校验 `source=session` 的 content 为 `ModelMessage` 类型。不使用 `Any` 或无约束 `object`。

#### Decision 3: Runtime 只依赖 ContextBuilder 的稳定入口

`AgentRuntimeKernel` 构造时注入 `ContextBuilder` 或等价 port。stream/execute 开始时调用 builder 构造一次上下文，并将最终 `visible_context_messages` 放入 `PatternRuntimeState`。Pattern 不直接认识 ContextBundle，避免把所有 pattern 重写为 context-aware。

替代方案：把 `ContextBundle` 放进 `PatternRuntimeState`。这更灵活，但会扩大当前 pattern 接口变更面；首期只需要替换上下文来源，不需要 pattern 参与预算决策。

#### Decision 4: Window 是 Builder 读取参数，Snip 是 Pipeline 策略

window 是 builder 的读取参数而非 pipeline 策略：builder 在查询 session messages 时直接按 `context_message_sequence` 水位与配置的最近 N 条限制读取范围（SQL WHERE/LIMIT），避免先读全量再在内存中裁剪。读取结果按 sequence 升序排列。

snipCompact 决定已装配 bundle 的裁剪：当 session message item 数超过阈值时，保留 pinned/高优先级 item、最近 K 条 item 与头部 H 条 item，移除中间 evictable item。

"头部消息"定义为按 sequence 排序的前 H 条 item（纯位置保留）。首期不按 role 区分。这保证会话开头的上下文（通常是首次 user 提问和 assistant 响应）不被裁掉。后续可按 pinned 标记或 role 细化头部保留策略。

分离后，后续可以改读取策略而不影响预算策略，也可以对 memory/tool/artifact item 单独加策略。

#### Decision 5: ReAct 临时 observations 不进入 ContextBundle

当前 ReAct 的 `PatternRuntimeState.observations` 是单个 run 内的 action result 回流机制。它包含模型响应、工具结果和模式内部状态，用于下一步 `Pattern.next_action()`。

`ContextBundle.tool_observations` 只预留给跨 step/跨 run 需要重新装配的持久化或待恢复 observation。首期为空，不从当前 observations 复制，避免同一工具结果被重复注入模型。

## Components

### contracts/context 或 src/context/schemas.py

首期可以将 schema 放在 `src/context/schemas.py`，若被其他模块公开复用，再提升到 `src/contracts/context.py`。跨 runtime 边界使用的对象必须类型明确。

核心对象：

```text
ContextItem
  source: session | memory | tool | artifact | rag | system
  type: message | summary | observation | artifact | chunk
  content: ModelMessage | dict[str, JsonValue]
  priority: int
  token_count: int | None
  pinned: bool
  evictable: bool
  metadata: dict

ContextBundle
  agent_run_id
  session_id
  session_messages: list[ContextItem]
  memory_summary: ContextItem | None
  tool_observations: list[ContextItem]
  artifacts: list[ContextItem]
  budget: ContextBudget | None
```

### ContextBuilder

职责：
- 从 AgentRun 读取 `session_id`、`context_message_sequence`。
- 通过 SessionManager 或 repository 读取水位内 session messages（按 window 配置限制最近 N 条）。
- 将 SessionMessage 转换为 ModelMessage 后创建 ContextItem（`content=ModelMessage`）。
- 执行 ContextStrategyPipeline（首期只有 snipCompact）。
- 输出 ContextBundle，其 `to_model_messages()` 从 session_messages items 中提取 `content` 即可，不做额外转换。

数据流路径：
```text
DB session_messages
  -> SessionManager.visible_history() -> list[SessionMessage]
  -> builder: to_model_messages() -> list[ModelMessage]        # 转换在此完成
  -> builder: wrap as ContextItem(content=ModelMessage)         # 包装
  -> ContextBundle.session_messages                              # 装配
  -> ContextStrategyPipeline.apply() (snipCompact)               # 裁剪
  -> ContextBundle.to_model_messages() -> extract content        # 提取，不再转换
  -> PatternRuntimeState.visible_context_messages
```

不负责：
- 调用模型摘要。
- 读取文件系统 artifact。
- 解析 provider token usage。
- 执行 runtime step 或写事件。

### ContextStrategyPipeline

`ContextStrategy` 接口接收 `ContextBundle` 并返回新 bundle 或等价拷贝。策略顺序由配置或 builder 默认值决定。

首期默认 pipeline 只包含一个策略：

```text
SnipCompactStrategy
```

Window 行为已在 builder 读取阶段完成（见 Decision 4），不作为 pipeline 策略。后续 memory/RAG/artifact 接入时可按需向 pipeline 添加独立策略。

### Runtime 集成

当前 `src/runtime/context.py` 中的 `RuntimeContextBuilder` 直接调用 `SessionManager.model_context()`，与本变更新增的 `src/context/builder.py` 职责重叠。本变更删除 `src/runtime/context.py`，将其逻辑合并到 `src/context/builder.py`，并更新所有引用。`AgentRuntimeKernel` 中第 169 行对 `SessionManager.model_context()` 的直接调用同步替换为注入的 ContextBuilder。

替换后 `AgentRuntimeKernel.stream()` 在创建 observations 前构造 context：

```text
context_bundle = await context_builder.build(current_run)
visible_context_messages = context_bundle.to_model_messages()
```

随后 pattern 仍接收：

```text
PatternRuntimeState(
  visible_context_messages=visible_context_messages,
  observations=observations,
  ...
)
```

这样不会破坏 `single_turn/chaining/routing/planning/react/reflection` 的现有模式实现。

## APIs

无外部 REST/SSE API 变化。

内部 Python API：

```text
ContextBuilder.build(agent_run: AgentRun) -> ContextBundle
ContextBundle.to_model_messages() -> list[ModelMessage]
ContextStrategy.apply(bundle: ContextBundle) -> ContextBundle
ContextStrategyPipeline.apply(bundle: ContextBundle) -> ContextBundle
```

配置项建议纳入现有 runtime/core config：

```text
context_window_messages: int               # window 读取的最近消息数，默认 50
context_snip_threshold_messages: int        # 触发 snip 的消息数阈值，默认 30
context_snip_head_messages: int             # snip 保留的头部消息数，默认 2
context_snip_tail_messages: int             # snip 保留的尾部消息数，默认 8
```

`context_token_budget` 不在首期配置中定义——当前没有消费者。token budget 留给后续引入 tokenizer/provider context window 选择时添加，避免用户配置了但无实际效果。

默认值应保证短会话不被裁剪（snip_threshold 大于典型短会话长度）。

## Data Model

无数据库 schema 变更。

`ContextItem` 与 `ContextBundle` 是运行时内存结构。首期只读取已有 `sessions` 与 `session_messages` 表：

```text
session_messages
  session_id
  sequence
  role
  content
  metadata
```

不新增 migration，不需要 rollback 脚本。回滚时恢复 runtime 直接调用 `SessionManager.model_context()` 的旧路径即可。

## Error Handling

- Session 不存在或水位无效：复用现有 `SessionManager` / repository 错误语义，向上保持 NotFound/Validation 类型，不在 context 层吞错。
- Context item 无法转换为 ModelMessage：抛出 context validation error，并使 AgentRun 失败，不提交 assistant final message。
- 策略配置非法：应用启动或 builder 初始化时失败；测试环境应覆盖默认 pipeline 可构造。
- 裁剪后无可用 user message：视为配置错误或非法上下文，返回可诊断错误，不调用模型。

## Security

- 首期 context 只读取用户可见 session messages，不读取文件、不执行命令、不访问网络。
- `snipCompact` 不把被裁剪内容写入事件或日志，避免意外扩大敏感信息暴露面。
- `ContextItem.metadata` 只能放安全元数据；不得存放 raw prompt、secret、authorization header。
- 后续 tool observation/artifact/RAG 接入时必须分别声明权限边界和审计策略，本变更不提前授权这些来源。

## Risks / Trade-offs

- [Risk] token_count 首期不精确，可能无法真实反映 provider context window。→ Mitigation：首期以 message 数和保守估算为主，真实 tokenizer 留给后续模型 profile/context budget 变更。
- [Risk] snip 保头保尾可能裁掉中间关键事实。→ Mitigation：默认阈值保守，优先保留 pinned/高优先级/最近用户输入；未来由 summary/memory 解决长程事实。
- [Risk] 引入 ContextBundle 但首期只填 session messages，抽象看起来超前。→ Mitigation：只新增当前主链路必需字段和空槽位，复杂策略不接入默认 pipeline。
- [Risk] runtime 注入 ContextBuilder 会影响大量测试。→ Mitigation：提供兼容默认 builder，并用 mock/fake builder 覆盖 kernel 测试。
- [Risk] autoCompact LLM 调用增加延迟和成本。→ Mitigation：仅在 token 预算紧张且有被驱逐内容时触发；失败时回退到无摘要裁剪，不阻塞 run。
- [Risk] observation 装配可能导致同一工具结果在模型上下文中重复。→ Mitigation：ContextBuilder 负责去重，以 call_id 为唯一标识。
- [Risk] 响应式恢复的渐进缩减可能过于激进，裁掉关键上下文。→ Mitigation：缩减只影响 evictable 内容和可截断大项；pinned/不可驱逐 item 始终保留。

## Spec 间依赖关系

```text
01-context-assembly-budgeting (基座)
    ├── 02-token-budget-and-counting (依赖 01 的 ContextItem/Bundle/Pipeline)
    │       ├── 03-advanced-compact-strategies (依赖 02 的 TokenCounter)
    │       └── 05-reactive-context-recovery (依赖 02 的 token 校验 + 03 的 microCompact)
    └── 04-observation-context-assembly (依赖 01 的 ContextBundle.tool_observations)
```

实施顺序：01 → 02 → 03 / 04（可并行） → 06。

Artifact 装配（原 05）与 RAG 检索留给后续独立 change，`ContextBundle.artifacts` 和 `ContextSource.RAG` 枚举值已预留。

## 新增组件设计

### TokenCounter 协议（02）

```text
TokenCounter(Protocol)
  count(text: str) -> int
  count_message(message: ModelMessage) -> int
  count_messages(messages: list[ModelMessage]) -> int

DefaultTokenCounter   # len(text) // 4，保守估算
TiktokenCounter       # 可选，依赖 tiktoken 包
```

- `ModelProfile` 新增 `context_window_tokens: int | None` 字段。
- `ContextBuilder` 注入 `TokenCounter`，装配完成后计算总 token 并与 `context_window_tokens - output_reserve` 比较。
- 配置新增 `CONTEXT_TOKEN_BUDGET: int`（全局默认，profile 未声明时使用）、`CONTEXT_TOKEN_RESERVE: int`（输出预留空间，默认 4096）。

### microCompact 策略（03）

截断单个 ContextItem 的 content 到配置的 token 上限。保留首部和尾部各 `micro_compact_keep_tokens` 个 token 的文本，中间以 `\n...[truncated]...\n` 替代。不调用 LLM。

配置：`CONTEXT_MICRO_COMPACT_MAX_ITEM_TOKENS: int`（默认 2000）、`CONTEXT_MICRO_COMPACT_KEEP_TOKENS: int`（默认 200）。

### toolResultBudget 策略（03）

限制 `ContextBundle.tool_observations` 的 token 总量。超出时按 priority 从低到高、时间从早到晚裁剪。pinned item 不裁。

配置：`CONTEXT_TOOL_RESULT_BUDGET_TOKENS: int`（默认 8000）。

### autoCompact 策略（03）

当 snipCompact 驱逐了中间内容时，autoCompact 将被驱逐的 messages 发送给当前 run 的模型，生成一段临时摘要作为 ContextItem（source=system, type=summary）插入 bundle。摘要不写入 Summary Memory，不持久化。

- LLM 调用失败时静默回退到无摘要的裁剪结果。
- 配置：`CONTEXT_AUTO_COMPACT_ENABLED: bool`（默认 false）。

### Observation 装配（04）

ContextBuilder 在构造 ContextBundle 时，从 `PatternRuntimeState.observations` 中提取 `kind="tool_result"` 的已完成 observation，转换为 ContextItem（source=tool, type=observation）放入 `ContextBundle.tool_observations`。

去重规则：以 `call_id` 为唯一标识，若 session messages 中已包含相同 call_id 的 tool result message，则不重复装配。

Pattern 仍从 `PatternRuntimeState.observations` 读取动作决策信息，不依赖 ContextBundle。


### ModelContextLengthError 与响应式恢复（05）

`src/exceptions/models.py` 新增：

```text
ModelContextLengthError(ModelError)
  retryable = True
  provider_reported_tokens: int | None
```

`src/models/parsers/errors.py` 在 provider 返回 413 或 error code 包含 `context_length_exceeded` 时映射为此类型。

`src/runtime/error_policy.py` 新增分支：
- 识别 `ModelContextLengthError`
- 若未发送可见 delta 且未进行过上下文缩减重试 → 返回 `context_reduction_retry` 决策
- 否则 → fail run

`src/runtime/kernel.py` 在 `_call_model()` 中：
- 收到 `context_reduction_retry` 决策后，以更激进参数重建 ContextBundle（降低 snip threshold + 启用 microCompact）
- 使用缩减后上下文重试
- 最多一次缩减重试

## Migration Plan

1. 新增 context schema、builder、pipeline 和 snipCompact 策略（01 已完成）。
2. 删除 `src/runtime/context.py`，注入 ContextBuilder 到 kernel（01 已完成）。
3. 实现 TokenCounter 协议与默认估算器，为 ModelProfile 增加 context_window_tokens，实现预飞行 token 校验。
4. 实现 microCompact、toolResultBudget 策略，接入 pipeline。
5. 实现 autoCompact 策略（默认关闭），接入 pipeline。
6. 实现 observation 装配：ContextBuilder 从 PatternRuntimeState 提取已完成 tool result。
7. 新增 ModelContextLengthError，更新 error parser 和 error_policy，实现 kernel 渐进缩减重试。
9. 跑全量 context/runtime/pattern 测试，确认无回归。
10. 更新 docs/结构说明。

回滚策略：按 spec 编号逆序回退，各 spec 独立可回滚。核心回滚路径：恢复 kernel 直接 SessionManager 调用（01 回滚）。无数据库变更，不需要 migration 回滚。

## Open Questions

- autoCompact 的 LLM 调用应使用当前 run 的模型还是单独配置的轻量模型？建议首期使用当前 run 模型，后续可配置独立摘要模型。
- artifact 引用从何处获取？建议首期由 AgentRun metadata 或请求参数传入，后续由 Skill/Task 系统提供。
