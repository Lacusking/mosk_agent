"""配置模块测试。"""


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

    def test_agent_runtime_defaults(self) -> None:
        """Agent runtime 默认配置可直接用于创建 run。"""
        from src.core.config import AgentRuntimeConfig

        config = AgentRuntimeConfig()

        assert config.DEFAULT_AGENT_MODE == "chat"
        assert config.DEFAULT_CHAT_PATTERN == "single_turn"
        assert config.DEFAULT_PLAN_PATTERN == "planning"
        assert config.DEFAULT_BUILD_PATTERN == "react"
        assert config.DEFAULT_REVIEW_PATTERN == "reflection"
        assert config.AGENT_RUN_MAX_STEPS == 12
        assert config.AGENT_RUN_TIMEOUT_SECONDS == 120
        assert config.AGENT_RUN_MODEL_RETRY_LIMIT == 1
        assert config.ENABLE_MOCK_TOOL_ACTIONS is True

    def test_agent_runtime_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """环境变量可以覆盖 Agent runtime 运行限制。"""
        monkeypatch.setenv("DEFAULT_AGENT_MODE", "build")
        monkeypatch.setenv("AGENT_RUN_MAX_STEPS", "8")
        monkeypatch.setenv("AGENT_RUN_TIMEOUT_SECONDS", "30")
        monkeypatch.setenv("AGENT_RUN_MODEL_RETRY_LIMIT", "0")
        monkeypatch.setenv("ENABLE_MOCK_TOOL_ACTIONS", "false")

        from src.core.config import AgentRuntimeConfig

        config = AgentRuntimeConfig()

        assert config.DEFAULT_AGENT_MODE == "build"
        assert config.AGENT_RUN_MAX_STEPS == 8
        assert config.AGENT_RUN_TIMEOUT_SECONDS == 30
        assert config.AGENT_RUN_MODEL_RETRY_LIMIT == 0
        assert config.ENABLE_MOCK_TOOL_ACTIONS is False

    @pytest.mark.parametrize(
        ("env_name", "env_value", "match"),
        [
            ("DEFAULT_AGENT_MODE", "task", "DEFAULT_AGENT_MODE"),
            ("DEFAULT_BUILD_PATTERN", "unknown", "默认 pattern"),
            ("AGENT_RUN_MAX_STEPS", "0", "greater than 0"),
            ("AGENT_RUN_MODEL_RETRY_LIMIT", "-1", "greater than or equal to 0"),
        ],
    )
    def test_agent_runtime_rejects_invalid_config(
        self,
        monkeypatch: pytest.MonkeyPatch,
        env_name: str,
        env_value: str,
        match: str,
    ) -> None:
        """非法 Agent runtime 配置在启动配置阶段失败。"""
        monkeypatch.setenv(env_name, env_value)

        from src.core.config import AgentRuntimeConfig

        with pytest.raises(ValueError, match=match):
            AgentRuntimeConfig()
