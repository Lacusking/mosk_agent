"""数据库连接测试（不依赖实际 DB 实例）。"""

from src.core.config import DBConfig


class TestDatabaseConfig:
    def test_database_url_format(self) -> None:
        db = DBConfig()
        url = db.database_url
        assert url.startswith("postgresql+asyncpg://")
        assert ":" in url
        assert "@" in url

    def test_default_port(self) -> None:
        db = DBConfig()
        assert db.DB_PORT == 5432

    def test_default_db_name(self) -> None:
        db = DBConfig()
        assert db.DB_NAME == "mosk_agent"
