## Why

当前仓库缺少可直接落地的“项目初始化阶段”规范拆分，导致脚手架、基础配置、core 工具、基础模型与存储基线之间职责边界不清，实施顺序与验收口径不一致。需要先把 Phase 1（初始化）拆成可独立实现与验收的能力单元，降低后续实现偏差。

## What Changes

- 新增“阶段 1 项目初始化”能力拆分，覆盖 0.1~0.5 五个初始化子阶段。
- 为每个子阶段定义独立需求场景、失败场景与验收标准。
- 输出统一设计文档，明确模块边界、依赖顺序与里程碑验证方式。
- 输出可执行任务清单，按 backend/database/testing/docs 拆分并附验证步骤。

## Capabilities

### New Capabilities
- `project-bootstrap-scaffold`: 定义初始化目录结构、依赖管理与开发规范落地要求。
- `base-runtime-configuration`: 定义配置管理、环境变量与日志初始化规范。
- `core-utilities-foundation`: 定义 core 层通用类型/枚举、异常体系、基础工具函数。
- `base-domain-model-foundation`: 定义 BaseModel、时间/ID、序列化基础能力。
- `storage-connectivity-foundation`: 定义 PostgreSQL、SQLAlchemy、Redis 的基础连接与健康检查。

### Modified Capabilities
- 无

## Impact

- Affected modules: `backend`, `database`, `testing`, `docs`
- API 兼容性影响：无新增外部业务 API，仅可能新增健康检查或内部探活端点
- 配置变更风险：新增环境变量与默认配置，需提供安全默认值
- 数据迁移风险：可能新增基础表或迁移脚本骨架，需提供回滚路径
- 关键假设：本阶段以 API+CLI MVP 基线推进；不引入 Web UI 与非 MVP 能力
- 非目标：不在本阶段实现复杂业务流程、RAG、完整评测体系
