"""配置模块测试。"""

import os

import pytest


class TestConfig:
    """配置加载测试。"""

    def test_default_config_loads(self) -> None:
        """配置有效时正常加载。"""
        from src.core.config import Config

        config = Config()
        assert config.app.ENVIRONMENT == "dev" or isinstance(config.app.ENVIRONMENT, str)
        assert config.app.VERSION
        assert config.db.DB_PORT == 5432
        assert config.redis.REDIS_PORT == 6379

    def test_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """环境变量覆盖默认值。"""
        monkeypatch.setenv("DB_HOST", "custom-host")
        monkeypatch.setenv("DB_PORT", "15432")

        from src.core.config import DBConfig

        db = DBConfig()
        assert db.DB_HOST == "custom-host"
        assert db.DB_PORT == 15432

    def test_database_url_format(self) -> None:
        """数据库 URL 格式正确。"""
        from src.core.config import DBConfig

        db = DBConfig()
        url = db.database_url
        assert url.startswith("postgresql+asyncpg://")
        assert str(db.DB_PORT) in url

    def test_missing_required_env_graceful(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """缺失必填配置时行为可预测（使用默认值）。"""
        monkeypatch.delenv("DB_NAME", raising=False)

        from src.core.config import DBConfig

        db = DBConfig()
        assert db.DB_NAME  # 有默认值，不会为空
