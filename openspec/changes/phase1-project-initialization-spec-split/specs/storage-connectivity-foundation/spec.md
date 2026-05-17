## ADDED Requirements

### Requirement: 存储基础层验证 PostgreSQL、SQLAlchemy 与 Redis 连接可用性
系统 MUST 提供存储基础组件，用于初始化 PostgreSQL、SQLAlchemy 会话基座与 Redis 客户端，并提供可验证的连接状态。

#### Scenario: 存储连接探活通过
- **WHEN** 存储初始化使用有效配置连接 PostgreSQL、SQLAlchemy 与 Redis
- **THEN** 每个已配置后端 MUST 返回 ready 状态
- **THEN** 运行时启动流程 MUST 允许继续执行

#### Scenario: 任一关键后端不可用时连接探活失败
- **WHEN** 任一必需存储后端不可达或认证失败
- **THEN** 系统 MUST 按配置策略阻断启动或使 readiness 失败
- **THEN** 诊断输出 MUST 指明失败后端与失败原因
