## 1. 0.1 项目脚手架（backend/docs）

- [ ] 1.1 [backend] 建立阶段 1 所需目录与入口骨架（应用入口、配置入口、core 入口、storage 入口）；验证：`tree -L 3 backend` 与约定结构一致。
- [ ] 1.2 [backend] 固化依赖管理与开发命令（安装、格式化、测试、启动）；验证：`make help`（或等效命令）可列出命令并可执行。
- [ ] 1.3 [docs] 编写初始化开发约定文档（目录职责、命名规则、提交约束）；验证：文档包含“目录职责 + 开发命令 + 验收步骤”。

## 2. 0.2 基础配置（backend/testing）

- [ ] 2.1 [backend] 实现集中配置加载（默认值 + 环境变量覆盖 + 必填项校验）；验证：`pytest -k config` 全通过。
- [ ] 2.2 [backend] 实现日志初始化（结构化日志、request_id/trace_id 注入）；验证：启动后首条日志包含关键字段。
- [ ] 2.3 [testing] 增加缺失配置失败用例；验证：缺失必填 env 时进程非 0 退出且输出缺失项。

## 3. 0.3 核心工具库（core）（backend/testing）

- [ ] 3.1 [backend] 新增 core 通用类型/枚举与结构化异常基类；验证：`pytest -k core_types or core_errors` 通过。
- [ ] 3.2 [backend] 新增基础工具函数（纯函数优先）并补充输入校验；验证：非法输入返回确定性错误。
- [ ] 3.3 [testing] 为 core 工具新增单测（成功/失败场景）；验证：测试覆盖成功路径与至少一个失败路径。

## 4. 0.4 数据模型基础（backend/testing）

- [ ] 4.1 [backend] 实现 BaseModel 基础能力（UUID 主键、created_at、updated_at）；验证：模型实例化后字段完整。
- [ ] 4.2 [backend] 实现时间/ID/序列化工具并统一输出契约；验证：序列化快照测试稳定通过。
- [ ] 4.3 [testing] 增加无效字段序列化失败用例；验证：返回结构化错误而非部分输出。

## 5. 0.5 存储基础（backend/database/testing）

- [ ] 5.1 [backend] 建立 PostgreSQL 连接与 SQLAlchemy session 基础组件；验证：健康检查可返回 DB ready。
- [ ] 5.2 [backend] 建立 Redis 客户端初始化与探活；验证：可执行 redis ping 并返回可观测状态。
- [ ] 5.3 [database] 增加初始化 migration 骨架（如基础元表/版本管理）并提供回滚脚本；验证：`alembic upgrade head` 与 `alembic downgrade -1` 均成功。
- [ ] 5.4 [testing] 增加存储连接失败用例（错误地址/凭据）；验证：启动失败并输出失败后端与原因。

## 6. 阶段里程碑验收与文档收敛（testing/docs/devops）

- [ ] 6.1 [testing] 执行阶段 1 集成验收（项目可启动、数据库可连接、基础工具可用）；验证：验收清单全部通过。
- [ ] 6.2 [docs] 更新阶段 1 README/运维说明（环境变量、启动方式、探活方式、回滚方式）；验证：新成员可按文档独立完成本地启动。
- [ ] 6.3 [devops] 补充 CI 最小校验流水（lint + unit test + migration check）；验证：PR 流水可稳定通过并拦截失败配置。
