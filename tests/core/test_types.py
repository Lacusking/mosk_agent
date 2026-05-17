"""core 通用类型/枚举测试。"""

from src.core.types import Environment
from src.core.types import RiskLevel
from src.core.types import StepType
from src.core.types import TaskStatus


class TestEnvironment:
    def test_values(self) -> None:
        assert Environment.DEV == "dev"
        assert Environment.STAGING == "staging"
        assert Environment.PRODUCTION == "production"

    def test_from_string(self) -> None:
        assert Environment("dev") == Environment.DEV


class TestTaskStatus:
    def test_all_statuses(self) -> None:
        statuses = [s.value for s in TaskStatus]
        assert "pending" in statuses
        assert "running" in statuses
        assert "completed" in statuses
        assert "failed" in statuses
        assert "cancelled" in statuses


class TestStepType:
    def test_all_types(self) -> None:
        types = [t.value for t in StepType]
        assert "model" in types
        assert "tool" in types


class TestRiskLevel:
    def test_ordering(self) -> None:
        assert RiskLevel.LOW < RiskLevel.MEDIUM < RiskLevel.HIGH < RiskLevel.CRITICAL

    def test_int_values(self) -> None:
        assert RiskLevel.LOW == 1
        assert RiskLevel.CRITICAL == 4
