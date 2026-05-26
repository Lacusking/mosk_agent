"""数据库 ORM contracts 基础模型测试。"""

from src.contracts.database import BaseModel
from src.contracts.database import PkModel
from src.contracts.database import TimestampedModel


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
