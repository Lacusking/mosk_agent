"""
项目配置

集中式配置加载：默认值 + 环境变量覆盖 + 必填项校验。
"""

import os
from pathlib import Path
from typing import ClassVar

from pydantic import Field
from pydantic import field_validator
from pydantic import model_validator
from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


class AppBaseSetting(BaseSettings):
    """基础配置，支持 .env 文件加载。"""

    model_config = SettingsConfigDict(
        env_file=os.path.join(str(Path(__file__).resolve().parents[2]), ".env"),
        extra="ignore",
    )


class DBConfig(AppBaseSetting):
    """PostgreSQL 数据库配置。"""

    DB_HOST: str = Field(default="localhost")
    DB_PORT: int = Field(default=5432)
    DB_NAME: str = Field(default="mosk_agent")
    DB_USER: str = Field(default="postgres")
    DB_PASS: str = Field(default="")

    @property
    def database_url(self) -> str:
        """构造异步数据库连接 URL。"""
        return (
            f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASS}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )


class RedisConfig(AppBaseSetting):
    """Redis 配置。"""

    REDIS_HOST: str = Field(default="localhost")
    REDIS_PORT: int = Field(default=6379)
    REDIS_PASS: str = Field(default="")
    REDIS_DB: int = Field(default=0)
    REDIS_TIMEOUT: int = Field(default=5)


class LogConfig(AppBaseSetting):
    """日志配置。"""

    LOG_LEVEL: str = Field(default="INFO")
    LOG_FORMAT: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(funcName)s:%(lineno)d - %(message)s"
    )
    LOG_DIR: str = Field(default="logs")
    LOG_FILE_MAX_SIZE: int = Field(default=1024 * 1024 * 10)
    LOG_FILE_BACKUP_COUNT: int = Field(default=7)
    ENABLE_CONSOLE: bool = Field(default=True)
    ENABLE_FILE: bool = Field(default=False)
    ENABLE_JSON: bool = Field(default=True)


class AppConfig(AppBaseSetting):
    """应用配置。"""

    VERSION: str = "0.1.0"
    SERVICE_TITLE: str = Field(default="MoskAgent")
    ENVIRONMENT: str = Field(default="dev")
    CORS_ORIGINS: str = Field(default="http://localhost:3000")
    CORS_ALLOW_CREDENTIALS: bool = Field(default=False)


class ModelProviderConfig(AppBaseSetting):
    """模型 provider 与传输默认配置。"""

    OPENAI_API_KEY: str = Field(default="")
    OPENAI_BASE_URL: str = Field(default="https://api.openai.com/v1")
    OPENAI_TIMEOUT_SECONDS: float = Field(default=30.0, gt=0)
    MOCK_TIMEOUT_SECONDS: float = Field(default=30.0, gt=0)


class AgentRuntimeConfig(AppBaseSetting):
    """AgentRun 与 pattern 选择的受控运行配置。"""

    _SUPPORTED_MODES: ClassVar[frozenset[str]] = frozenset({"chat", "plan", "build", "review"})
    _SUPPORTED_PATTERNS: ClassVar[frozenset[str]] = frozenset(
        {"single_turn", "chaining", "routing", "planning", "react", "reflection"}
    )

    DEFAULT_AGENT_MODE: str = Field(default="chat")
    DEFAULT_CHAT_PATTERN: str = Field(default="single_turn")
    DEFAULT_PLAN_PATTERN: str = Field(default="planning")
    DEFAULT_BUILD_PATTERN: str = Field(default="react")
    DEFAULT_REVIEW_PATTERN: str = Field(default="reflection")
    AGENT_RUN_MAX_STEPS: int = Field(default=12, gt=0)
    AGENT_RUN_TIMEOUT_SECONDS: float = Field(default=120.0, gt=0)
    AGENT_RUN_MODEL_RETRY_LIMIT: int = Field(default=1, ge=0)
    ENABLE_MOCK_TOOL_ACTIONS: bool = Field(default=True)
    CONTEXT_WINDOW_MESSAGES: int = Field(default=50, gt=0)
    CONTEXT_SNIP_THRESHOLD_MESSAGES: int = Field(default=30, gt=0)
    CONTEXT_SNIP_HEAD_MESSAGES: int = Field(default=2, ge=0)
    CONTEXT_SNIP_TAIL_MESSAGES: int = Field(default=8, ge=0)
    CONTEXT_TOKEN_BUDGET: int = Field(default=32768, gt=0)
    CONTEXT_TOKEN_RESERVE: int = Field(default=4096, ge=0)
    CONTEXT_MICRO_ITEM_MAX_TOKENS: int = Field(default=4096, gt=0)
    CONTEXT_TOOL_RESULT_BUDGET_TOKENS: int = Field(default=8192, gt=0)

    @field_validator("DEFAULT_AGENT_MODE")
    @classmethod
    def validate_mode(cls, value: str) -> str:
        """校验默认 Agent mode。

        Args:
            value: 待校验的 mode。

        Returns:
            已校验的 mode。

        Raises:
            ValueError: mode 不在当前支持集合内。
        """
        if value not in cls._SUPPORTED_MODES:
            raise ValueError("DEFAULT_AGENT_MODE 不受支持")
        return value

    @field_validator(
        "DEFAULT_CHAT_PATTERN",
        "DEFAULT_PLAN_PATTERN",
        "DEFAULT_BUILD_PATTERN",
        "DEFAULT_REVIEW_PATTERN",
    )
    @classmethod
    def validate_pattern(cls, value: str) -> str:
        """校验默认 pattern 名称。

        Args:
            value: 待校验的 pattern。

        Returns:
            已校验的 pattern。

        Raises:
            ValueError: pattern 不在当前支持集合内。
        """
        if value not in cls._SUPPORTED_PATTERNS:
            raise ValueError("默认 pattern 不受支持")
        return value

    @model_validator(mode="after")
    def validate_default_mode_pattern(self) -> "AgentRuntimeConfig":
        """确认默认 mode 对应的 pattern 已配置。

        Returns:
            已校验的 Agent runtime 配置。

        Raises:
            ValueError: 默认 mode 没有对应 pattern 配置。
        """
        mode_to_pattern = {
            "chat": self.DEFAULT_CHAT_PATTERN,
            "plan": self.DEFAULT_PLAN_PATTERN,
            "build": self.DEFAULT_BUILD_PATTERN,
            "review": self.DEFAULT_REVIEW_PATTERN,
        }
        if not mode_to_pattern[self.DEFAULT_AGENT_MODE]:
            raise ValueError("DEFAULT_AGENT_MODE 缺少对应默认 pattern")
        if self.CONTEXT_SNIP_HEAD_MESSAGES + self.CONTEXT_SNIP_TAIL_MESSAGES > (
            self.CONTEXT_SNIP_THRESHOLD_MESSAGES
        ):
            raise ValueError("CONTEXT_SNIP_HEAD_MESSAGES 与 CONTEXT_SNIP_TAIL_MESSAGES 之和不能超过阈值")
        if self.CONTEXT_SNIP_THRESHOLD_MESSAGES > self.CONTEXT_WINDOW_MESSAGES:
            raise ValueError("CONTEXT_SNIP_THRESHOLD_MESSAGES 不能大于 CONTEXT_WINDOW_MESSAGES")
        if self.CONTEXT_TOKEN_RESERVE >= self.CONTEXT_TOKEN_BUDGET:
            raise ValueError("CONTEXT_TOKEN_RESERVE 必须小于 CONTEXT_TOKEN_BUDGET")
        if self.CONTEXT_MICRO_ITEM_MAX_TOKENS >= self.CONTEXT_TOKEN_BUDGET:
            raise ValueError("CONTEXT_MICRO_ITEM_MAX_TOKENS 必须小于 CONTEXT_TOKEN_BUDGET")
        if self.CONTEXT_TOOL_RESULT_BUDGET_TOKENS >= self.CONTEXT_TOKEN_BUDGET:
            raise ValueError("CONTEXT_TOOL_RESULT_BUDGET_TOKENS 必须小于 CONTEXT_TOKEN_BUDGET")
        return self


class Config(BaseSettings):
    """聚合配置入口。"""

    db: DBConfig = DBConfig()
    redis: RedisConfig = RedisConfig()
    log: LogConfig = LogConfig()
    app: AppConfig = AppConfig()
    models: ModelProviderConfig = ModelProviderConfig()
    agent_runtime: AgentRuntimeConfig = AgentRuntimeConfig()


settings = Config()
