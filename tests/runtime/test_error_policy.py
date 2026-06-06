"""runtime 模型错误策略测试。"""

from src.exceptions import ModelContextLengthError
from src.runtime.error_policy import decide_model_error


def test_context_length_error_triggers_single_reduction_retry() -> None:
    """首次上下文超限触发缩减重试。"""
    decision = decide_model_error(
        ModelContextLengthError(),
        retry_count=0,
        retry_limit=1,
        visible_output_sent=False,
    )

    assert decision.retry is True
    assert decision.context_reduction_retry is True
    assert decision.fail_run is False


def test_context_length_error_does_not_retry_after_visible_output() -> None:
    """已有可见输出时不执行上下文缩减重试。"""
    decision = decide_model_error(
        ModelContextLengthError(),
        retry_count=0,
        retry_limit=1,
        visible_output_sent=True,
    )

    assert decision.retry is False
    assert decision.context_reduction_retry is False
    assert decision.fail_run is True


def test_context_length_error_retries_only_once_per_step() -> None:
    """同一步第二次上下文超限直接失败。"""
    decision = decide_model_error(
        ModelContextLengthError(),
        retry_count=1,
        retry_limit=3,
        visible_output_sent=False,
    )

    assert decision.retry is False
    assert decision.context_reduction_retry is False
    assert decision.fail_run is True
