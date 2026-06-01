"""模型结果到 AgentRun finish reason 的映射。"""

from src.contracts.agent_runs import AgentRunFinishReason
from src.contracts.runtime import ModelResponse
from src.contracts.runtime import ModelResponseStatus
from src.contracts.runtime import ModelStopReason


def finish_reason_from_model_response(response: ModelResponse) -> AgentRunFinishReason:
    """根据统一模型响应推导 AgentRun 完成原因。

    Args:
        response: 模型最终响应。

    Returns:
        AgentRun finish reason。
    """
    if response.status == ModelResponseStatus.REFUSED:
        return AgentRunFinishReason.REFUSED
    if response.status == ModelResponseStatus.INCOMPLETE:
        if response.stop_reason == ModelStopReason.MAX_TOKENS:
            return AgentRunFinishReason.INCOMPLETE
        return AgentRunFinishReason.INCOMPLETE
    return AgentRunFinishReason.COMPLETED


__all__ = ["finish_reason_from_model_response"]
