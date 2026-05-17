"""contracts 基础模型测试。"""

from uuid import UUID

from src.contracts.base import BaseModel
from src.contracts.base import PkModel
from src.contracts.base import TimestampedModel


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
        columns = {c.name for c in PkModel.__table__.columns} if hasattr(PkModel, "__table__") else set()
        # PkModel is abstract, check via column definitions
        assert "id" in PkModel.__dict__ or hasattr(PkModel, "id")


class TestTimestampedModel:
    def test_is_abstract(self) -> None:
        assert TimestampedModel.__abstract__ is True

    def test_has_timestamp_attrs(self) -> None:
        assert hasattr(TimestampedModel, "created_at")
        assert hasattr(TimestampedModel, "updated_at")
