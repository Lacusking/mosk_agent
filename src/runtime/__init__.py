"""Agent runtime 基础组件。"""

from src.runtime.cancellation import CancellationRegistry
from src.runtime.cancellation import CancellationToken
from src.runtime.cancellation import CancellationTrigger
from src.runtime.cancellation import CancelledError
from src.runtime.error_policy import ModelErrorDecision
from src.runtime.error_policy import decide_model_error
from src.runtime.factory import RuntimeModelSelection
from src.runtime.factory import RuntimeModelTarget
from src.runtime.factory import build_mock_model_invoker
from src.runtime.factory import build_openai_model_invoker
from src.runtime.factory import build_runtime_model_invoker
from src.runtime.factory import build_runtime_model_target
from src.runtime.finish_reason import finish_reason_from_model_response
from src.runtime.kernel import AgentRunExecutionResult
from src.runtime.kernel import AgentRuntimeKernel
from src.runtime.model_invoker import RuntimeModelInvoker
from src.runtime.state_machine import can_transition
from src.runtime.state_machine import ensure_transition
from src.runtime.stream import format_sse
from src.runtime.stream import output_text_delta_event
from src.runtime.stream import run_started_event
from src.runtime.stream import terminal_event

__all__ = [
    "CancellationRegistry",
    "CancellationToken",
    "CancellationTrigger",
    "CancelledError",
    "AgentRunExecutionResult",
    "AgentRuntimeKernel",
    "ModelErrorDecision",
    "RuntimeModelInvoker",
    "RuntimeModelSelection",
    "RuntimeModelTarget",
    "build_mock_model_invoker",
    "build_openai_model_invoker",
    "build_runtime_model_invoker",
    "build_runtime_model_target",
    "can_transition",
    "decide_model_error",
    "ensure_transition",
    "finish_reason_from_model_response",
    "format_sse",
    "output_text_delta_event",
    "run_started_event",
    "terminal_event",
]
