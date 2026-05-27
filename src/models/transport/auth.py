"""Provider 凭证与认证头构建边界。"""

from src.exceptions import ModelConfigurationError


def build_openai_headers(api_key: str) -> dict[str, str]:
    """构建 OpenAI transport 请求头。

    Args:
        api_key: OpenAI API key，仅在 transport 边界中使用。

    Returns:
        OpenAI 认证与 content type 请求头。

    Raises:
        ModelConfigurationError: API key 未配置。
    """
    if not api_key:
        raise ModelConfigurationError(provider="openai", operation="invoke")
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
