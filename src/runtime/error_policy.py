"""Runtime 模型错误处理策略。"""

from dataclasses import dataclass

from src.exceptions import ModelError
from src.exceptions import ModelStreamInterruptedError


@dataclass(frozen=True)
class ModelErrorDecision:
    """runtime 对模型错误的处理决策。"""

    retry: bool
    fail_run: bool
    error_type: str


def decide_model_error(
    error: ModelError,
    *,
    retry_count: int,
    retry_limit: int,
    visible_output_sent: bool,
) -> ModelErrorDecision:
    """根据模型错误与当前输出状态决定 runtime 行为。

    Args:
        error: 标准化模型错误。
        retry_count: 当前已重试次数。
        retry_limit: 最大重试次数。
        visible_output_sent: 是否已经向客户端发送公开可见 delta。

    Returns:
        处理决策。
    """
    if isinstance(error, ModelStreamInterruptedError) and visible_output_sent:
        return ModelErrorDecision(
            retry=False,
            fail_run=True,
            error_type=error.__class__.__name__,
        )
    can_retry = error.retryable and not visible_output_sent and retry_count < retry_limit
    return ModelErrorDecision(
        retry=can_retry,
        fail_run=not can_retry,
        error_type=error.__class__.__name__,
    )


__all__ = ["ModelErrorDecision", "decide_model_error"]
