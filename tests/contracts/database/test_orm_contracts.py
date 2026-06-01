"""数据库 ORM contracts 基础模型测试。"""

from datetime import UTC
from datetime import datetime

from src.contracts.database import BaseModel
from src.contracts.database import PkModel
from src.contracts.database import TimestampedModel
from src.storage.database.time import aware_utc_from_db
from src.storage.database.time import naive_utc_for_db
from src.storage.database.time import naive_utc_now


class TestBaseModel:
    def test_is_abstract(self) -> None:
        assert BaseModel.__abstract__ is True

    def test_metadata_naming_convention(self) -> None:
        nc = BaseModel.metadata.naming_convention
        assert "pk" in nc
        assert "fk" in nc
        assert "ix" in nc


class TestPkModel:
    def test_is_abstract(self) -> None:
        assert PkModel.__abstract__ is True

    def test_has_id_column(self) -> None:
        assert "id" in PkModel.__dict__ or hasattr(PkModel, "id")


class TestTimestampedModel:
    def test_is_abstract(self) -> None:
        assert TimestampedModel.__abstract__ is True

    def test_has_timestamp_attrs(self) -> None:
        assert hasattr(TimestampedModel, "created_at")
        assert hasattr(TimestampedModel, "updated_at")

    def test_onupdate_timestamp_is_naive_utc(self) -> None:
        value = naive_utc_now()

        assert value.tzinfo is None

    def test_repository_boundary_datetime_is_aware_utc(self) -> None:
        value = aware_utc_from_db(datetime(2026, 5, 26, 12))

        assert value is not None
        assert value.tzinfo is UTC

    def test_repository_boundary_datetime_accepts_none(self) -> None:
        assert aware_utc_from_db(None) is None

    def test_db_boundary_datetime_is_naive_utc(self) -> None:
        value = naive_utc_for_db(datetime(2026, 5, 26, 20, tzinfo=UTC))

        assert value is not None
        assert value.hour == 20
        assert value.tzinfo is None
