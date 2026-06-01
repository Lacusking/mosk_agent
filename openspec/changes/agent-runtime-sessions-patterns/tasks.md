## 1. 前置契约与配置（src/contracts, src/models, src/core）

- [x] 1.1 [agent-run-runtime][src/contracts/runtime, src/models, testing] 完成前置 `model-runtime-event-contracts` 的 `agent_run_id` 修订并确认本变更可依赖的新 event envelope/metadata；验证：`rg "task_id" src/contracts/runtime src/models/selector.py tests/contracts/runtime` 无旧执行关联字段且 `pytest -q tests/contracts tests/models` 通过。
- [x] 1.2 [agent-run-runtime][src/exceptions, src/api] 为 `BaseError` 增加 `http_status` 属性，各子类按语义覆盖（401/403/404/409/422），新增 `AgentRunConflictError`，更新 exception handler 以 `exc.http_status` 决定 HTTP 状态码；验证：`pytest -q tests/exceptions tests/api -k "http_status or conflict"` 通过。
- [x] 1.3 [session-conversation-history][agent-run-runtime][src/contracts] 定义 Session/Message、AgentRun/AgentRunStep、运行级 stream payload 与 API 输入输出 contracts；验证：`pytest -q tests/contracts -k "session or agent_run or stream"` 通过。
- [x] 1.4 [agent-pattern-orchestration][minimal-tool-action-port][src/contracts] 定义 PatternRuntimeState/NextAction（含模型动作的 `internal`/`public_output` 可见性）判别契约、ChainConfig/ChainStage、RoutingConfig/RoutingRule 及 ToolActionRequest/Result/安全失败 payload；验证：`pytest -q tests/contracts -k "pattern or tool_action or chain or routing"` 通过。
- [x] 1.5 [agent-run-runtime][agent-pattern-orchestration][src/core] 增加默认 mode/pattern、run max steps/timeout/retry limit 与 dev/test mock tool 开关配置校验；验证：`pytest -q tests/core -k config` 通过。

## 2. 数据库与持久化基座（database, src/storage/database）

- [x] 2.1 [session-conversation-history][agent-run-runtime][database] 编写 Alembic migration 创建 `sessions`、`session_messages`、`agent_runs`、`agent_run_steps`、`runtime_events` 表、UUID/时间字段、外键与查询索引；验证：在测试 PostgreSQL 上执行 `alembic upgrade head` 成功并检查表结构。
- [x] 2.2 [agent-run-runtime][database] 增加同 session 活动 run 的 partial unique index、消息/event/step 序号唯一约束及 downgrade 删除路径；验证：`alembic downgrade -1 && alembic upgrade head` 通过，并以数据库测试验证并发约束。
- [x] 2.3 [session-conversation-history][src/storage/database] 实现 Session 与 SessionMessage ORM/repository 的创建、查找、按 sequence 追加和有序读取；验证：`pytest -q tests/sessions -k repository` 通过。
- [x] 2.4 [agent-run-runtime][src/storage/database] 实现 AgentRun/AgentRunStep ORM/repository、状态条件更新与按 run 查询步骤；验证：`pytest -q tests/agent_runs -k repository` 通过。
- [x] 2.5 [agent-run-runtime][src/storage/database] 实现低频 RuntimeEvent store 的 append 与 `agent_run_id` timeline 查询，扩展 run/pattern/tool 事实 payload；验证：`pytest -q tests/events -k "append or timeline or security"` 通过。

## 3. 会话与运行服务（src/sessions, src/agent_runs）

- [x] 3.1 [session-conversation-history][src/sessions] 实现 SessionManager 的创建、历史读取与 user/final-assistant 消息提交，确保中间输出不写历史；验证：`pytest -q tests/sessions -k manager` 通过。
- [x] 3.2 [session-conversation-history][src/sessions] 实现创建 run 时原子写入用户输入并固定 `context_message_sequence` 的流程；验证：`pytest -q tests/sessions -k watermark` 通过。
- [x] 3.3 [agent-run-runtime][src/agent_runs] 实现 AgentRunManager 的创建、终态提交、冲突映射和同 session 活动 run 串行约束处理；验证：`pytest -q tests/agent_runs -k "manager or concurrent"` 通过。

## 4. Pattern 基础与选择（src/patterns）

- [x] 4.1 [agent-pattern-orchestration][src/patterns] 实现 Pattern 协议、NextAction 构造、registry、mode 默认映射与 selector 的显式覆盖/回退/拒绝逻辑；验证：`pytest -q tests/patterns -k "registry or selector or modes"` 通过。
- [x] 4.2 [agent-pattern-orchestration][src/patterns] 实现 `single_turn` 与 `chaining` 策略及 observation 到下一模型动作/完成动作的转换；验证：`pytest -q tests/patterns -k "single_turn or chaining"` 通过。
- [x] 4.3 [agent-pattern-orchestration][src/patterns] 实现 `routing` 的目标 pattern 转移与 `planning` 的规划输出策略，确保不创建 Task/todo/Markdown 数据；验证：`pytest -q tests/patterns -k "routing or planning"` 通过，并断言无 Task 写入依赖。
- [x] 4.4 [agent-pattern-orchestration][src/patterns] 实现 `reflection` 的 draft/critique/revise 执行状态和最终 action；验证：`pytest -q tests/patterns -k reflection` 通过。
- [x] 4.5 [agent-pattern-orchestration][src/patterns] 实现 `react` 的内部模型意图、tool observation 回流、公开最终答案动作、完成与 max steps 终止策略；验证：`pytest -q tests/patterns -k react` 通过。

## 5. 最小 Tool Action Port（src/tools）

- [x] 5.1 [minimal-tool-action-port][src/tools] 定义 `ToolActionExecutor` port、mock registry 和标准工具校验/执行错误，使 runtime 只接受完成校验的 tool call；验证：`pytest -q tests/tools -k "port or validation"` 通过。
- [x] 5.2 [minimal-tool-action-port][src/tools] 实现无 IO 副作用的确定性 `mock.echo`/`mock.lookup` executor 与安全审计信息构造；验证：`pytest -q tests/tools -k mock` 通过，测试断言未进行网络/文件/命令调用。
- [ ] 5.3 [minimal-tool-action-port][testing] 增加未注册工具、非法参数、失败 observation 与敏感参数不写事件的安全测试；验证：`pytest -q tests/tools tests/events -k "failure or security"` 通过。

## 6. Runtime Kernel 与 Streaming（src/runtime）

- [x] 6.1 [agent-run-runtime][agent-pattern-orchestration][src/runtime] 实现 kernel 动作循环与 step/event 生命周期，将模型 observation 反馈给 pattern 并以 AgentRun 终态结束；验证：`pytest -q tests/runtime -k "kernel or state_machine"` 通过。
- [x] 6.2 [agent-run-runtime][src/runtime] 接入既有 `ModelAdapter.stream`/`ModelStreamReducer`，仅将 `public_output` 模型动作映射为 `output.text.delta`，输出 `run.started`/terminal SSE payload，且不持久化任何 delta；验证：`pytest -q tests/runtime -k "stream or visibility"` 通过并断言 internal draft/route/tool 内容不出现在 SSE。
- [x] 6.3 [agent-run-runtime][src/runtime] 实现模型错误策略：可见输出前有限重试、输出后中断失败、拒绝残缺 tool arguments 和 incomplete/refused finish 映射；验证：`pytest -q tests/runtime -k "error or retry or interrupted or finish"` 通过。
- [x] 6.4 [agent-run-runtime][src/runtime] 实现取消令牌（显式请求与 SSE 断连）、持久化取消转换和未完成内容不得提交 Session 的保护；验证：`pytest -q tests/runtime -k "cancel or sse_disconnect"` 通过。
- [x] 6.5 [agent-run-runtime][minimal-tool-action-port][src/runtime] 将 `InvokeToolAction` 接入 mock executor、审计事件和 observation 回流；验证：`pytest -q tests/runtime tests/tools -k "tool_action or react"` 通过。

## 7. Service API（src/api）

- [x] 7.1 [session-conversation-history][src/api] 增加认证保护的 Session create/get/messages 路由与统一普通响应 schema；验证：`pytest -q tests/api -k session` 通过并检查 OpenAPI 路由。
- [x] 7.2 [agent-run-runtime][src/api] 增加认证保护的 AgentRun create/get/events/cancel 路由，校验 session、mode、pattern 与冲突错误响应；验证：`pytest -q tests/api -k agent_run` 通过并检查 OpenAPI 路由。
- [x] 7.3 [agent-run-runtime][src/api] 为 `POST /api/v1/agent-runs` 的 `stream=true` 增加 SSE response 输出和 terminal failure/cancel 映射；验证：`pytest -q tests/api -k sse` 通过。

## 8. 端到端验收与文档（testing, docs）

- [ ] 8.1 [session-conversation-history][agent-run-runtime][testing] 增加 Mock 模型单轮流式执行集成测试，覆盖会话历史、水位、事件查询和最终消息提交；验证：`pytest -q tests/integration -k "agent_run and single_turn"` 通过。
- [ ] 8.2 [agent-pattern-orchestration][testing] 增加 single_turn、chaining 与 planning 集成测试，覆盖 chaining 多阶段传递与中间阶段不可见、planning 文本完成且不创建 Task；验证：`pytest -q tests/integration -k "single_turn or chaining or planning"` 通过。
- [ ] 8.3 [agent-pattern-orchestration][minimal-tool-action-port][testing] 增加 react、reflection 与 routing 集成测试，覆盖 ReAct `internal model -> mock tool -> observation -> public final` 闭环、reflection draft/critique 不可见、routing 规则命中与模型 fallback 转移；验证：`pytest -q tests/integration -k "react or reflection or routing"` 通过。
- [ ] 8.4 [agent-run-runtime][testing] 增加并发 session 冲突、stream interruption、显式 cancel、SSE 断连取消、认证失败与事件脱敏回归测试；验证：`pytest -q tests/integration -k "concurrent or interrupted or cancel or sse_disconnect or security"` 通过。
- [x] 8.5 [agent-run-runtime][docs] 更新 API/架构说明与运行配置文档，说明 `agent_run_id`、SSE 断连策略、mock-only tools、Task 非执行语义和 migration/rollback 路径；验证：人工核对文档与 OpenAPI/schema 名称一致。
- [ ] 8.6 [agent-run-runtime][testing] 执行整体质量校验并处理本变更引入的 typing/lint/test 回归；验证：`ruff check src tests && pytest -q` 通过。
