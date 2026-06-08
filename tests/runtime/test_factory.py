"""runtime 模型工厂测试。"""

import pytest

from src.contracts.runtime import ModelProtocol
from src.core.config import ModelProviderConfig
from src.exceptions import ModelConfigurationError
from src.runtime import RuntimeModelSelection
from src.runtime import build_openai_model_invoker
from src.runtime import build_runtime_model_target


def test_runtime_factory_builds_default_mock_target() -> None:
    """默认配置保持 mock runtime target。"""
    target = build_runtime_model_target(ModelProviderConfig())

    assert target.provider == "mock"
    assert target.model == "mock-model"
    assert target.protocol == ModelProtocol.MOCK


def test_runtime_factory_builds_openai_target() -> None:
    """OpenAI 配置会构造 OpenAI runtime target。"""
    config = ModelProviderConfig(
        OPENAI_API_KEY="sk-test",
        RUNTIME_MODEL_PROVIDER="openai",
        RUNTIME_MODEL_NAME="gpt-test",
        RUNTIME_MODEL_PROTOCOL="openai_responses",
        RUNTIME_MODEL_CONTEXT_WINDOW_TOKENS=128000,
    )

    target = build_runtime_model_target(config)

    assert target.provider == "openai"
    assert target.model == "gpt-test"
    assert target.protocol == ModelProtocol.OPENAI_RESPONSES


def test_runtime_factory_agent_run_selection_overrides_config_default() -> None:
    """单次 AgentRun 的模型选择可覆盖配置默认。"""
    config = ModelProviderConfig(
        OPENAI_API_KEY="sk-test",
        RUNTIME_MODEL_PROVIDER="mock",
        RUNTIME_MODEL_NAME="mock-model",
        RUNTIME_MODEL_PROTOCOL="mock",
    )

    target = build_runtime_model_target(
        config,
        RuntimeModelSelection(
            provider="openai",
            model="gpt-override",
            protocol=ModelProtocol.OPENAI_CHAT,
            context_window_tokens=64000,
        ),
    )

    assert target.provider == "openai"
    assert target.model == "gpt-override"
    assert target.protocol == ModelProtocol.OPENAI_CHAT


def test_runtime_factory_rejects_openai_without_api_key() -> None:
    """OpenAI provider 缺少 API key 时在工厂阶段失败。"""
    config = ModelProviderConfig(
        RUNTIME_MODEL_PROVIDER="openai",
        RUNTIME_MODEL_NAME="gpt-test",
        RUNTIME_MODEL_PROTOCOL="openai_chat",
    )

    with pytest.raises(ModelConfigurationError):
        build_openai_model_invoker(config)
