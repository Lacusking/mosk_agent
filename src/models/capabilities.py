"""模型请求能力的调用前校验。"""

from src.contracts.runtime import ImageContentBlock
from src.contracts.runtime import ModelRequest
from src.contracts.runtime import ModelResponseFormatType
from src.exceptions import ModelCapabilityError
from src.exceptions import ModelInvalidRequestError
from src.models.profiles import ModelProfile


def validate_request_capabilities(request: ModelRequest, profile: ModelProfile) -> None:
    """在传输前校验请求所需能力和受控选项。

    Args:
        request: 待执行的模型请求。
        profile: 已选择的模型 profile。

    Raises:
        ModelCapabilityError: 请求需要 profile 未提供的能力。
        ModelInvalidRequestError: 请求包含 profile 不允许的生成选项。
    """
    required: list[tuple[bool, bool, str]] = [
        (bool(request.tools), profile.capabilities.tool_calling, "tool_calling"),
        (request.stream, profile.capabilities.streaming, "streaming"),
        (
            request.response_format is not None
            and request.response_format.type != ModelResponseFormatType.TEXT,
            profile.capabilities.structured_output,
            "structured_output",
        ),
        (
            any(
                isinstance(block, ImageContentBlock)
                for message in request.messages
                for block in message.content
            ),
            profile.capabilities.vision,
            "vision",
        ),
    ]
    for requested, supported, name in required:
        if requested and not supported:
            raise ModelCapabilityError(
                provider=profile.provider,
                model=profile.model,
                protocol=profile.protocol.value,
                operation="select",
                data={"capability": name},
            )

    provided_options = {
        name
        for name in request.options.model_fields_set
        if getattr(request.options, name) not in (None, {}, [])
    }
    unsupported_options = provided_options - profile.allowed_options
    if unsupported_options:
        raise ModelInvalidRequestError(
            provider=profile.provider,
            model=profile.model,
            protocol=profile.protocol.value,
            operation="select",
            data={"unsupported_options": sorted(unsupported_options)},
        )
