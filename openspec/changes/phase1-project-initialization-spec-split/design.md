## Context

本变更用于将“阶段 1 项目初始化（0.1~0.5）”拆成可独立实现与验收的能力单元，避免一次性初始化任务范围过大、责任不清。当前仓库尚未形成一致的初始化交付口径，需要在实现前先固定能力边界、依赖顺序和验收规则。

约束：
- 以 `openspec/project.md` 的 MVP 基线推进（API+CLI、OpenAI+Mock、Summary Memory、单租户）。
- 采用最小实现路径，不引入非 MVP 能力。

## Goals / Non-Goals

**Goals:**
- 建立阶段 1 的五个能力规范：脚手架、基础配置、core 工具、基础模型、存储连接。
- 明确模块依赖顺序：0.1 -> 0.2 -> 0.3 -> 0.4 -> 0.5。
- 为后续实现提供统一验收标准：项目可启动、数据库可连接、基础工具可用。

**Non-Goals:**
- 不实现业务功能（任务编排、复杂 workflow、RAG、评测体系）。
- 不引入 Web UI、多租户强隔离或生产级 sandbox。
- 不扩展阶段 1 之外的能力清单。

## Architecture

采用“初始化能力分层”架构：
1. Bootstrap Layer（0.1）：目录、依赖、开发规范。
2. Configuration Layer（0.2）：配置加载、环境变量、日志。
3. Core Utilities Layer（0.3）：类型/枚举、异常、工具函数。
4. Model Foundation Layer（0.4）：BaseModel、时间/ID、序列化。
5. Storage Foundation Layer（0.5）：PostgreSQL/SQLAlchemy/Redis 连接能力。

集成关系：仅在现有模块边界内补齐基础能力，不替换既有业务模块。

## Components

- `src/core`:
  - 通用类型/枚举、结构化异常基类、基础工具函数
  - 配置模块（settings/env）与日志初始化
- `src/contracts`:
  - 基础模型抽象（BaseModel + 通用字段）、序列化约定
- `src/storage`:
  - 存储连接组件（PostgreSQL/SQLAlchemy session、Redis client）
  - 基础 migration 骨架与连接验证
- `src/api`:
  - FastAPI 入口脚手架与健康检查端点
- `src/cli`:
  - Typer CLI 入口脚手架与诊断命令
- `testing`:
  - 初始化链路 smoke test（启动、配置、连接、工具函数）
- `docs`:
  - 初始化阶段说明、环境变量说明、验收流程

## APIs

本阶段不引入业务 API，仅允许新增初始化可观测相关端点（如健康检查）并遵守：
- REST 风格
- `/api/v1` 前缀
- 统一响应结构 `{code,msg,data}`

CLI 侧允许新增初始化与诊断命令（例如配置检查/连接探活），并保持退出码可脚本化。

## Data Model

- 基础实体字段约束：
  - 主键：UUID（遵循项目约定）
  - 时间字段：`created_at`、`updated_at`
- 不在本阶段引入业务实体复杂关系。
- 仅提供后续模块可复用的基础模型与序列化约定。

## Decisions

1. 采用“5 个 capability 对应 5 份 spec”而非单一大 spec。
- 原因：更易并行与逐步验收，减少跨模块冲突。
- 备选：单 spec 覆盖全部初始化。
- 不选原因：任务不可追踪、失败定位成本高。

2. 先定义可验收规范，再进入实现。
- 原因：阶段初始化涉及跨模块，先固化验收口径可避免返工。
- 备选：直接编码后补文档。
- 不选原因：与当前 spec-driven 流程冲突。

3. 存储阶段仅做“连接基础”而非业务 schema 设计。
- 原因：符合 MVP 最小路径。
- 备选：提前设计业务数据模型。
- 不选原因：超出阶段目标。

## Risks / Trade-offs

- [Risk] 初始化能力拆分过细导致文档维护成本上升  
  -> Mitigation：保持每个 capability 聚焦单一目标，统一验收模板。
- [Risk] 环境差异导致连接探活不稳定  
  -> Mitigation：定义本地默认配置与失败回退提示。
- [Risk] 规范与实际代码结构偏离  
  -> Mitigation：在 tasks 中加入文档同步与验收校验步骤。

## Migration Plan

1. 先提交本 change 的 proposal/design/specs/tasks。
2. 进入 `/opsx:apply` 执行初始化实现。
3. 先落地 0.1~0.3，再落地 0.4~0.5。
4. 每步执行 smoke test（启动、配置加载、工具可用、DB/Redis 可连接）。
5. 回滚策略：
   - 代码回滚：按 capability 粒度回退变更。
   - 数据库回滚：通过 Alembic downgrade 撤销本阶段 migration。
   - 配置回滚：恢复默认 env 与连接配置。

## Open Questions

- 是否需要在阶段 1 明确 Redis 为“必须可连接”还是“可选连接并降级”？
- CLI 初始化诊断命令是否在本阶段提供最小实现，还是仅保留接口占位？
