"""上下文配置测试。"""

import pytest

from src.core.config import AgentRuntimeConfig


def test_context_config_defaults_are_conservative() -> None:
    """默认 context 配置可直接用于短会话。"""
    config = AgentRuntimeConfig()

    assert config.CONTEXT_WINDOW_MESSAGES == 50
    assert config.CONTEXT_SNIP_THRESHOLD_MESSAGES == 30
    assert config.CONTEXT_SNIP_HEAD_MESSAGES == 2
    assert config.CONTEXT_SNIP_TAIL_MESSAGES == 8


def test_context_config_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """环境变量可以覆盖 context 配置。"""
    monkeypatch.setenv("CONTEXT_WINDOW_MESSAGES", "12")
    monkeypatch.setenv("CONTEXT_SNIP_THRESHOLD_MESSAGES", "10")
    monkeypatch.setenv("CONTEXT_SNIP_HEAD_MESSAGES", "2")
    monkeypatch.setenv("CONTEXT_SNIP_TAIL_MESSAGES", "4")

    config = AgentRuntimeConfig()

    assert config.CONTEXT_WINDOW_MESSAGES == 12
    assert config.CONTEXT_SNIP_THRESHOLD_MESSAGES == 10
    assert config.CONTEXT_SNIP_HEAD_MESSAGES == 2
    assert config.CONTEXT_SNIP_TAIL_MESSAGES == 4


@pytest.mark.parametrize(
    "values",
    [
        {"CONTEXT_WINDOW_MESSAGES": 0},
        {"CONTEXT_SNIP_THRESHOLD_MESSAGES": 0},
        {"CONTEXT_SNIP_HEAD_MESSAGES": 3, "CONTEXT_SNIP_TAIL_MESSAGES": 3, "CONTEXT_SNIP_THRESHOLD_MESSAGES": 5},
        {"CONTEXT_WINDOW_MESSAGES": 5, "CONTEXT_SNIP_THRESHOLD_MESSAGES": 6},
    ],
)
def test_context_config_rejects_invalid_values(values: dict[str, int]) -> None:
    """非法 context 配置在启动配置阶段失败。"""
    with pytest.raises(ValueError):
        AgentRuntimeConfig(**values)
