# 项目目录结构说明

```
src/
├── access/              # 接入层：统一处理 Web/API/CLI/Webhook/A2A/MCP 等入口请求，做请求归一化
├── identity/            # 身份与租户：用户、租户、组织、项目、角色、API Key、RBAC/ABAC 权限模型
├── api/                 # HTTP API 服务：FastAPI 路由、依赖注入、接口 schema、管理端 API
├── cli/                 # 命令行工具：本地运行 Agent、调试任务、回放轨迹、执行评估
├── core/                # 公共基础组件：通用类型、枚举、异常、ID 生成、时间、JSON、Result 封装
├── contracts/           # 统一协议与数据契约：Message、Task、Event、Tool、Agent、Memory 等 Pydantic Schema
│
├── runtime/             # Agent 运行时内核：事件循环、调度器、状态机、Step Runner、Checkpoint、Replay
├── events/              # 事件系统：Event Sourcing、Event Store、Event Bus、事件流、事件处理器
├── tasks/               # 任务管理：Task、TaskStep、Task Graph、DAG、状态、进度、任务仓储
├── sessions/            # 会话管理：Session、对话历史、上下文压缩、会话生命周期、会话状态持久化
├── scheduler/           # 平台级调度器：定时任务、延迟任务、周期任务、后台任务、锁、租约、队列
│
├── models/              # 模型适配层：OpenAI、Anthropic、Gemini、Ollama、LiteLLM、模型选择与降级
├── prompts/             # Prompt 引擎：模板管理、变量解析、格式化、版本管理、结构化输出、Prompt Pack
├── skills/              # Skill 能力引擎：将 Prompt、Tool、Workflow、Policy、Memory Scope 组合为可复用能力包
├── hooks/               # Hook 生命周期扩展：before/after model/tool/memory/task 等拦截器与治理注入点
├── patterns/            # Agentic 设计模式：提示链、路由、并行化、规划、反思、自修正、资源优化
├── workflow/            # 确定性工作流引擎：DAG、步骤流转、条件分支、重试、补偿、Workflow 版本管理
│
├── agents/              # Agent 抽象层：BaseAgent、SupervisorAgent、WorkerAgent、Role Agent、内置 Agent
├── multi_agent/         # 多智能体协作：任务委派、Subagent 生命周期、上下文隔离、结果聚合、A2A/MCP 协议边界
│
├── tools/               # 工具系统：工具定义、注册、路由、执行、Schema 校验、权限、重试、幂等、MCP 工具适配
├── connectors/          # 外部系统连接器：GitHub、Slack、Jira、数据库、浏览器、Google Drive 等 API 封装
├── context/             # 上下文管理：上下文组装、裁剪、压缩、Token Budget、工具结果格式化、结构化输出解析
├── memory/              # 记忆系统：Session、Working、Summary、Semantic、Entity、Episodic Memory 及写入/遗忘策略
├── knowledge/           # 知识资产管理：语料、文档、解析、切分、索引、元数据、权限、来源追踪
├── rag/                 # 检索增强生成：Retriever、Embedding、Reranker、Citation、Grounding、知识片段注入
│
├── vfs/                 # 虚拟文件系统：/workspace、/artifacts、/memories，文件权限、快照、diff、挂载后端
├── artifacts/           # 产物管理：报告、代码补丁、图表、数据集、Notebook、文件预览、版本、导出、血缘
├── sandbox/             # 沙箱执行环境：Docker、Firecracker、Python Runner、Browser Runner、资源限制、网络隔离
│
├── policy/              # 策略引擎：工具策略、模型策略、Memory 策略、Sandbox 策略、数据访问策略、策略决策
├── governance/          # 治理与安全：风险分级、人工审批、审计、Guardrails、Secret Scope、合规规则
├── observability/       # 可观测性：Tracing、Metrics、Logging、Cost Tracking、Token Usage、Alerts、Dashboard
├── evaluation/          # 评估系统：轨迹评估、工具调用评估、最终答案评估、安全评估、回归测试、Replay Debug
├── experiments/         # 实验系统：Prompt A/B、模型 A/B、路由策略实验、Memory Policy 实验、灰度发布指标
├── notifications/       # 通知系统：审批通知、任务完成通知、失败告警、Webhook、Slack、Email、站内通知
│
├── control_plane/       # 控制面：Agent、Skill、Tool、Prompt、Policy、Memory、Eval、Deployment 的管理服务
├── deployment/          # 部署与版本：Agent/Skill/Prompt/Policy 发布、环境绑定、灰度、回滚、lockfile
├── storage/             # 存储层：PostgreSQL、Redis、对象存储、向量库、Repository、ORM Model
├── workers/             # 异步 Worker：Runtime Worker、Tool Worker、Memory Worker、Sandbox Worker、Eval Worker
└── plugins/             # 插件系统：第三方 Tool、Skill、Hook、Model Adapter、Connector 的加载与扩展机制
```

## 架构分层说明

| 层级 | 目录 | 职责 |
|------|------|------|
| **接入与接口层** | access, identity, api, cli | 统一入口处理、身份认证、权限控制、API 服务、CLI 工具 |
| **基础与契约层** | core, contracts | 公共组件、类型定义、异常处理、统一数据契约 |
| **运行时核心层** | runtime, events, tasks, sessions, scheduler | Agent 执行内核、事件驱动、任务编排、会话管理、调度系统 |
| **智能能力层** | models, prompts, skills, hooks, patterns, workflow | 模型适配、Prompt 引擎、Skill 封装、生命周期钩子、设计模式、工作流 |
| **Agent 层** | agents, multi_agent | Agent 抽象与实现、单 Agent 与多 Agent 协作、A2A/MCP 协议 |
| **工具与知识层** | tools, connectors, context, memory, knowledge, rag | 工具系统、外部连接器、上下文管理、记忆系统、知识资产、RAG |
| **资源管理层** | vfs, artifacts, sandbox | 虚拟文件系统、产物管理、安全沙箱执行环境 |
| **治理与策略层** | policy, governance, observability | 策略引擎、风险治理、安全审批、可观测性 |
| **运营与评估层** | evaluation, experiments, notifications | 效果评估、实验系统、通知告警 |
| **基础设施层** | control_plane, deployment, storage, workers, plugins | 控制面、部署发布、存储、异步 Worker、插件扩展 |

## 核心数据流

```
[接入层] → [运行时核心] → [Agent层] → [工具/知识层]
                              ↓
                    [模型层] ← [上下文/记忆层]
                              ↓
                    [治理/策略层] 贯穿始终
                              ↓
                    [可观测性层] 采集全链路
```

## 关键设计原则

1. **契约优先** - contracts 定义所有模块间交互的数据结构
2. **事件驱动** - 核心模块通过 events 解耦，支持 Event Sourcing
3. **策略可插拔** - policy + hooks 实现治理逻辑的灵活注入
4. **Skill 即能力单元** - 将 Prompt + Tool + Workflow + Policy 打包为可复用技能
5. **A2A/MCP 边界清晰** - multi_agent 处理协议边界，agents 处理内部抽象
6. **全链路可观测** - observability 覆盖执行轨迹、成本、Token 使用
