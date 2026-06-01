"""无外部副作用的 Mock 工具 executor。"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from src.contracts.runtime import JsonValue
from src.contracts.runtime import ModelToolDeclaration
from src.contracts.tools import ToolActionRequest
from src.contracts.tools import ToolActionResult
from src.contracts.tools import ToolActionStatus


@dataclass(frozen=True)
class MockToolDefinition:
    """Mock 工具定义。"""

    name: str
    handler: Callable[[dict[str, JsonValue]], JsonValue]
    required_arguments: frozenset[str] = frozenset()


class MockToolActionExecutor:
    """确定性的无 IO Mock 工具 executor。"""

    def __init__(self, tools: list[MockToolDefinition] | None = None) -> None:
        """初始化 executor。

        Args:
            tools: 可选自定义 mock 工具列表。
        """
        registered = tools or [
            MockToolDefinition(
                name="mock.echo",
                handler=lambda arguments: {"echo": arguments},
            ),
            MockToolDefinition(
                name="mock.lookup",
                handler=lambda arguments: {
                    "key": arguments.get("key"),
                    "value": f"mock:{arguments.get('key', '')}",
                },
                required_arguments=frozenset({"key"}),
            ),
            MockToolDefinition(
                name="lookup",
                handler=lambda arguments: {
                    "key": arguments.get("key") or arguments.get("query"),
                    "value": f"mock:{arguments.get('key') or arguments.get('query', '')}",
                },
                required_arguments=frozenset(),
            ),
        ]
        self._tools = {tool.name: tool for tool in registered}

    async def execute(self, request: ToolActionRequest) -> ToolActionResult:
        """执行 mock 工具动作。

        Args:
            request: 工具动作请求。

        Returns:
            工具动作结果。
        """
        tool = self._tools.get(request.name)
        if tool is None:
            return _failure(request, "ToolNotRegistered", ToolActionStatus.VALIDATION_FAILED)
        missing = sorted(tool.required_arguments.difference(request.arguments))
        if missing:
            return ToolActionResult(
                call_id=request.call_id,
                name=request.name,
                status=ToolActionStatus.VALIDATION_FAILED,
                observation={"missing_arguments": missing},
                is_error=True,
                error_type="ToolArgumentsInvalid",
            )
        try:
            observation = tool.handler(dict(request.arguments))
        except Exception as exc:  # noqa: BLE001
            return ToolActionResult(
                call_id=request.call_id,
                name=request.name,
                status=ToolActionStatus.EXECUTION_FAILED,
                observation={"message": "mock tool execution failed"},
                is_error=True,
                error_type=exc.__class__.__name__,
            )
        return ToolActionResult(
            call_id=request.call_id,
            name=request.name,
            status=ToolActionStatus.SUCCESS,
            observation=observation,
            is_error=False,
        )

    def registered_names(self) -> list[str]:
        """返回已注册 mock 工具名。

        Returns:
            按名称排序的工具名列表。
        """
        return sorted(self._tools)

    def declarations(self) -> list[ModelToolDeclaration]:
        """返回已注册 mock 工具的模型声明。

        Returns:
            可传入 ModelRequest 的工具声明列表。
        """
        result: list[ModelToolDeclaration] = []
        for tool in self._tools.values():
            required = sorted(tool.required_arguments)
            schema: dict[str, Any] = {"type": "object"}
            if required:
                schema["required"] = required
            result.append(
                ModelToolDeclaration(
                    name=tool.name,
                    description=f"Mock tool: {tool.name}",
                    parameters_schema=schema,
                    strict=True,
                )
            )
        return sorted(result, key=lambda d: d.name)


def _failure(
    request: ToolActionRequest,
    error_type: str,
    status: ToolActionStatus,
) -> ToolActionResult:
    return ToolActionResult(
        call_id=request.call_id,
        name=request.name,
        status=status,
        observation={"tool_name": request.name},
        is_error=True,
        error_type=error_type,
    )


__all__ = ["MockToolActionExecutor", "MockToolDefinition"]
