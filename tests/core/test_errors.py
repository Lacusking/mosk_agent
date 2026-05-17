"""结构化异常测试。"""

import pytest

from src.core.errors import AuthenticationError
from src.core.errors import BaseError
from src.core.errors import ConfigurationError
from src.core.errors import ForbiddenError
from src.core.errors import NotFoundError
from src.core.errors import StorageError
from src.core.errors import ValidationError


class TestBaseError:
    def test_default_message(self) -> None:
        err = BaseError()
        assert err.msg == "未知错误"
        assert err.code == 50000

    def test_custom_message(self) -> None:
        err = BaseError(msg="自定义错误", data={"key": "value"})
        assert err.msg == "自定义错误"
        assert err.data == {"key": "value"}

    def test_to_dict(self) -> None:
        err = BaseError(msg="测试", data={"x": 1})
        d = err.to_dict()
        assert d["code"] == 50000
        assert d["msg"] == "测试"
        assert d["data"] == {"x": 1}

    def test_to_dict_without_data(self) -> None:
        err = BaseError(msg="测试")
        d = err.to_dict()
        assert "data" not in d

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

    def test_not_found_error(self) -> None:
        err = NotFoundError(msg="用户不存在")
        assert err.code == 40400
        assert err.msg == "用户不存在"

    def test_authentication_error(self) -> None:
        err = AuthenticationError()
        assert err.code == 40100

    def test_forbidden_error(self) -> None:
        err = ForbiddenError()
        assert err.code == 40300

    def test_configuration_error(self) -> None:
        err = ConfigurationError()
        assert err.code == 50001

    def test_storage_error(self) -> None:
        err = StorageError()
        assert err.code == 50002
