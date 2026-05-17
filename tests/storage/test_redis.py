"""Redis 配置测试（不依赖实际 Redis 实例）。"""

from src.core.config import RedisConfig


class TestRedisConfig:
    def test_default_host(self) -> None:
        cfg = RedisConfig()
        assert cfg.REDIS_HOST == "localhost"

    def test_default_port(self) -> None:
        cfg = RedisConfig()
        assert cfg.REDIS_PORT == 6379

    def test_default_timeout(self) -> None:
        cfg = RedisConfig()
        assert cfg.REDIS_TIMEOUT == 5
