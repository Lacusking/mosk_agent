## ADDED Requirements

### Requirement: 平台必须提供唯一正式异常入口
系统 MUST 通过 `src.exceptions` 提供 `BaseError` 及平台公共异常类型，并将现有应用代码对平台异常的引用迁移至该入口。`src.core.errors` MUST NOT 继续作为公共或兼容导出入口。

#### Scenario: 现有异常消费者迁移到正式入口
- **GIVEN** API 异常处理、鉴权依赖或测试需要引用平台异常
- **WHEN** 本变更完成异常迁移
- **THEN** 这些消费者 MUST 从 `src.exceptions` 引用所需异常
- **THEN** 仓库应用代码 MUST 不再依赖 `src.core.errors`

#### Scenario: 通用异常仍保留结构化响应语义
- **GIVEN** 调用方构造继承自 `BaseError` 的平台异常
- **WHEN** 异常被序列化为错误响应
- **THEN** 结果 MUST 包含机器可读错误码与人类可读错误消息
- **THEN** 非空且允许公开的附加数据 MUST 可通过结构化字段返回

### Requirement: Models 必须提供可供 runtime 决策的专属错误
系统 MUST 定义继承自平台 `BaseError` 的 `ModelError` 层级，并为模型调用错误提供稳定分类和决策元数据，而不是要求调用方识别 provider 原始异常。

#### Scenario: 可重试服务错误被归一化
- **GIVEN** 模型 provider 返回限流、超时或暂时不可用错误
- **WHEN** models 层映射该失败
- **THEN** 系统 MUST 返回对应的模型专属错误分类
- **THEN** 错误 MUST 标识 `retryable=true`
- **THEN** 若 provider 返回 retry-after 信息，错误 MUST 保留其标准化值

#### Scenario: 非重试配置或请求错误被归一化
- **GIVEN** 模型调用因凭证无效、权限不足、请求非法或能力不支持而失败
- **WHEN** models 层映射该失败
- **THEN** 系统 MUST 返回对应模型专属错误分类
- **THEN** 错误 MUST 标识 `retryable=false`

#### Scenario: 流在产生部分输出后中断
- **GIVEN** 一次模型 streaming 调用已经产生文本或工具参数片段
- **WHEN** 连接在完成事件前中断
- **THEN** 系统 MUST 返回可区分于普通传输失败的 stream interruption 错误
- **THEN** 错误 MUST 允许后续 runtime 判断已有部分输出或未完成工具意图的处理方式

### Requirement: 模型错误不得泄露敏感 provider 数据
系统 MUST 在模型异常及其可序列化数据中排除凭证、authorization header 与未脱敏的 provider 原始请求内容。

#### Scenario: Provider 鉴权失败内容被安全映射
- **GIVEN** provider 在包含鉴权上下文的请求上返回认证失败
- **WHEN** models 层生成公开错误对象
- **THEN** 公开错误 MUST 包含 provider、错误分类及安全的诊断字段
- **THEN** 公开错误 MUST NOT 包含 API key、认证头或完整原始请求载荷
