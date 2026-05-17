"""core 工具函数测试。"""

import pytest

from src.core.utils import calculate_md5
from src.core.utils import camel_to_snake
from src.core.utils import format_datetime
from src.core.utils import generate_uuid
from src.core.utils import generate_uuid7
from src.core.utils import utc_now


class TestGenerateUuid:
    def test_returns_string(self) -> None:
        result = generate_uuid()
        assert isinstance(result, str)
        assert len(result) == 36  # UUID v4 format

    def test_unique(self) -> None:
        ids = {generate_uuid() for _ in range(100)}
        assert len(ids) == 100


class TestGenerateUuid7:
    def test_returns_string(self) -> None:
        result = generate_uuid7()
        assert isinstance(result, str)
        assert len(result) == 36


class TestUtcNow:
    def test_returns_datetime(self) -> None:
        from datetime import datetime

        result = utc_now()
        assert isinstance(result, datetime)
        assert result.tzinfo is not None


class TestCamelToSnake:
    def test_basic(self) -> None:
        assert camel_to_snake("CamelCase") == "camel_case"

    def test_multi_words(self) -> None:
        assert camel_to_snake("CamelCaseExample") == "camel_case_example"

    def test_single_word(self) -> None:
        assert camel_to_snake("Word") == "word"

    def test_empty_string_raises(self) -> None:
        with pytest.raises(ValueError, match="不能为空"):
            camel_to_snake("")


class TestCalculateMd5:
    def test_string_input(self) -> None:
        result = calculate_md5("hello")
        assert isinstance(result, str)
        assert len(result) == 32

    def test_bytes_input(self) -> None:
        result = calculate_md5(b"hello")
        assert isinstance(result, str)
        assert len(result) == 32

    def test_consistent(self) -> None:
        assert calculate_md5("test") == calculate_md5("test")

    def test_different_inputs(self) -> None:
        assert calculate_md5("a") != calculate_md5("b")


class TestFormatDatetime:
    def test_iso_format(self) -> None:
        dt = utc_now()
        result = format_datetime(dt)
        assert isinstance(result, str)
        assert "T" in result
