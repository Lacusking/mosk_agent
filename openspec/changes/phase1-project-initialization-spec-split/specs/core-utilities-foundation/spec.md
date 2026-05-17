## ADDED Requirements

### Requirement: core 基础库提供可复用类型、异常与工具函数
系统 MUST 提供可复用的 core 基础能力，包括通用类型/枚举、结构化异常体系与纯函数工具，以支撑跨模块复用。

#### Scenario: 模块复用 core 契约
- **WHEN** 后端模块需要使用通用类型、枚举或异常定义
- **THEN** 模块 MUST 从 core 基础库导入，而不是本地重复定义
- **THEN** 共享异常对象 MUST 同时保留机器可读错误码与人类可读错误信息

#### Scenario: 工具函数输入非法时确定性失败
- **WHEN** core 工具函数接收非法输入
- **THEN** 系统 MUST 抛出结构化异常或返回文档化失败结果
- **THEN** 失败输出 MUST 可通过自动化测试稳定断言
