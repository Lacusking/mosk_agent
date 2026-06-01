"""AgentRun 业务编排服务。"""

from uuid import uuid4

from src.contracts.agent_runs import AgentMode
from src.contracts.agent_runs import AgentRun
from src.contracts.agent_runs import AgentRunFinishReason
from src.contracts.agent_runs import AgentRunStatus
from src.contracts.agent_runs import AgentRunStep
from src.contracts.agent_runs import AgentRunStepKind
from src.contracts.agent_runs import AgentRunStepStatus
from src.core.config import AgentRuntimeConfig
from src.core.utils import utc_now
from src.exceptions import AgentRunConflictError
from src.storage.database.repositories import AgentRunRepository


class AgentRunManager:
    """协调 AgentRun 创建、step 创建与终态提交。"""

    def __init__(
        self,
        *,
        repository: AgentRunRepository,
        config: AgentRuntimeConfig,
    ) -> None:
        """初始化 manager。

        Args:
            repository: AgentRun 持久化访问对象。
            config: Agent runtime 配置。
        """
        self._repository = repository
        self._config = config

    async def create_run(
        self,
        *,
        session_id: str,
        input_message_id: str,
        mode: AgentMode,
        active_pattern: str,
        context_message_sequence: int,
        requested_pattern: str | None = None,
    ) -> AgentRun:
        """创建 AgentRun 并执行同 Session 活动运行冲突检查。

        Args:
            session_id: 所属 Session id。
            input_message_id: 用户输入消息 id。
            mode: 请求 mode。
            active_pattern: selector 已确定的 pattern。
            context_message_sequence: 本次运行上下文水位。
            requested_pattern: 用户显式请求的 pattern。

        Returns:
            创建后的 AgentRun。

        Raises:
            AgentRunConflictError: 同一 Session 已有活动运行。
        """
        if await self._repository.has_active_run(session_id):
            raise AgentRunConflictError(data={"session_id": session_id})
        return await self._repository.create_run(
            session_id=session_id,
            input_message_id=input_message_id,
            mode=mode,
            requested_pattern=requested_pattern,
            active_pattern=active_pattern,
            context_message_sequence=context_message_sequence,
            trace_id=str(uuid4()),
            max_steps=self._config.AGENT_RUN_MAX_STEPS,
            timeout_seconds=self._config.AGENT_RUN_TIMEOUT_SECONDS,
            retry_limit=self._config.AGENT_RUN_MODEL_RETRY_LIMIT,
        )

    async def mark_running(self, agent_run_id: str) -> AgentRun | None:
        """将 AgentRun 标记为 running。

        Args:
            agent_run_id: AgentRun id。

        Returns:
            更新后的 AgentRun；不存在或已终态则返回 None。
        """
        return await self._repository.transition_run(
            agent_run_id=agent_run_id,
            status=AgentRunStatus.RUNNING,
        )

    async def create_step(
        self,
        *,
        agent_run_id: str,
        kind: AgentRunStepKind,
        pattern: str,
        invocation_id: str | None = None,
        safe_input: dict[str, object] | None = None,
    ) -> AgentRunStep:
        """创建 AgentRunStep。

        Args:
            agent_run_id: AgentRun id。
            kind: step 类型。
            pattern: 当前 pattern。
            invocation_id: 可选模型 invocation id。
            safe_input: 脱敏输入摘要。

        Returns:
            创建后的 AgentRunStep。
        """
        return await self._repository.create_step(
            agent_run_id=agent_run_id,
            kind=kind,
            pattern=pattern,
            invocation_id=invocation_id,
            safe_input=safe_input,
        )

    async def complete_step(
        self,
        *,
        step_id: str,
        safe_output: dict[str, object] | None = None,
    ) -> AgentRunStep | None:
        """标记 step 成功。

        Args:
            step_id: step id。
            safe_output: 脱敏输出摘要。

        Returns:
            更新后的 step；不存在时返回 None。
        """
        return await self._repository.complete_step(
            step_id=step_id,
            status=AgentRunStepStatus.SUCCEEDED,
            safe_output=safe_output,
        )

    async def fail_step(
        self,
        *,
        step_id: str,
        error_type: str,
        safe_output: dict[str, object] | None = None,
    ) -> AgentRunStep | None:
        """标记 step 失败。

        Args:
            step_id: step id。
            error_type: 失败分类。
            safe_output: 脱敏输出摘要。

        Returns:
            更新后的 step；不存在时返回 None。
        """
        return await self._repository.complete_step(
            step_id=step_id,
            status=AgentRunStepStatus.FAILED,
            safe_output=safe_output,
            error_type=error_type,
        )

    async def complete_run(
        self,
        agent_run_id: str,
        *,
        finish_reason: AgentRunFinishReason = AgentRunFinishReason.COMPLETED,
    ) -> AgentRun | None:
        """将 AgentRun 标记为 completed。

        Args:
            agent_run_id: AgentRun id。
            finish_reason: 完成原因。

        Returns:
            更新后的 AgentRun；不存在或已终态则返回 None。
        """
        return await self._repository.transition_run(
            agent_run_id=agent_run_id,
            status=AgentRunStatus.COMPLETED,
            finish_reason=finish_reason,
            completed_at=utc_now().replace(tzinfo=None),
        )

    async def fail_run(self, agent_run_id: str, *, error_type: str) -> AgentRun | None:
        """将 AgentRun 标记为 failed。

        Args:
            agent_run_id: AgentRun id。
            error_type: 失败分类。

        Returns:
            更新后的 AgentRun；不存在或已终态则返回 None。
        """
        return await self._repository.transition_run(
            agent_run_id=agent_run_id,
            status=AgentRunStatus.FAILED,
            finish_reason=AgentRunFinishReason.ERROR,
            error_type=error_type,
            completed_at=utc_now().replace(tzinfo=None),
        )

    async def cancel_run(self, agent_run_id: str) -> AgentRun | None:
        """将 AgentRun 标记为 cancelled。

        Args:
            agent_run_id: AgentRun id。

        Returns:
            更新后的 AgentRun；不存在或已终态则返回 None。
        """
        return await self._repository.transition_run(
            agent_run_id=agent_run_id,
            status=AgentRunStatus.CANCELLED,
            finish_reason=AgentRunFinishReason.CANCELLED,
            completed_at=utc_now().replace(tzinfo=None),
        )

    async def set_active_pattern(
        self,
        *,
        agent_run_id: str,
        active_pattern: str,
    ) -> AgentRun | None:
        """更新 AgentRun 当前 active pattern。

        Args:
            agent_run_id: AgentRun id。
            active_pattern: 新的 active pattern。

        Returns:
            更新后的 AgentRun；不存在或已终态则返回 None。
        """
        return await self._repository.set_active_pattern(
            agent_run_id=agent_run_id,
            active_pattern=active_pattern,
        )


__all__ = ["AgentRunManager"]
