"""
项目配置

集中式配置加载：默认值 + 环境变量覆盖 + 必填项校验。
"""

import os
from pathlib import Path

from pydantic import Field
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


class Config(BaseSettings):
    """聚合配置入口。"""

    db: DBConfig = DBConfig()
    redis: RedisConfig = RedisConfig()
    log: LogConfig = LogConfig()
    app: AppConfig = AppConfig()


settings = Config()
