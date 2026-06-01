"""平台通用结构化异常测试。"""

from src.exceptions import AgentRunConflictError
from src.exceptions import AuthenticationError
from src.exceptions import BaseError
from src.exceptions import ConfigurationError
from src.exceptions import ForbiddenError
from src.exceptions import NotFoundError
from src.exceptions import StorageError
from src.exceptions import ValidationError


class TestBaseError:
    def test_default_message(self) -> None:
        err = BaseError()
        assert err.msg == "未知错误"
        assert err.code == 50000
        assert err.http_status == 400

    def test_custom_message(self) -> None:
        err = BaseError(msg="自定义错误", data={"key": "value"})
        assert err.msg == "自定义错误"
        assert err.data == {"key": "value"}

    def test_to_dict(self) -> None:
        err = BaseError(msg="测试", data={"x": 1})
        assert err.to_dict() == {"code": 50000, "msg": "测试", "data": {"x": 1}}

    def test_to_dict_without_data(self) -> None:
        err = BaseError(msg="测试")
        assert err.to_dict() == {"code": 50000, "msg": "测试"}

    def test_is_exception(self) -> None:
        err = BaseError(msg="test")
        assert isinstance(err, Exception)
        assert str(err) == "test"

    def test_cause_chain(self) -> None:
        original = ValueError("原始错误")
        err = BaseError(msg="包装错误", cause=original)
        assert err.cause is original


class TestSpecificErrors:
    def test_validation_error(self) -> None:
        err = ValidationError()
        assert err.code == 40000
        assert err.msg == "参数校验失败"
        assert err.http_status == 422

    def test_not_found_error(self) -> None:
        err = NotFoundError(msg="用户不存在")
        assert err.code == 40400
        assert err.msg == "用户不存在"
        assert err.http_status == 404

    def test_authentication_error(self) -> None:
        err = AuthenticationError()
        assert err.code == 40100
        assert err.http_status == 401

    def test_forbidden_error(self) -> None:
        err = ForbiddenError()
        assert err.code == 40300
        assert err.http_status == 403

    def test_agent_run_conflict_error(self) -> None:
        err = AgentRunConflictError()
        assert err.code == 40901
        assert err.msg == "AgentRun 冲突"
        assert err.http_status == 409

    def test_configuration_error(self) -> None:
        assert ConfigurationError().code == 50001

    def test_storage_error(self) -> None:
        assert StorageError().code == 50002
