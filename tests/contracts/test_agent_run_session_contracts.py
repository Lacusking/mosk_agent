"""Session、AgentRun 与运行级 stream 契约测试。"""

from datetime import UTC
from datetime import datetime

import pytest
from pydantic import ValidationError

from src.contracts import AgentMode
from src.contracts import AgentRun
from src.contracts import AgentRunFinishReason
from src.contracts import AgentRunStatus
from src.contracts import AgentRunStreamEvent
from src.contracts import AgentRunStep
from src.contracts import AgentRunStepKind
from src.contracts import AgentRunStepStatus
from src.contracts import CreateAgentRunRequest
from src.contracts import CreateSessionRequest
from src.contracts import OutputTextDeltaStreamPayload
from src.contracts import RunStartedStreamPayload
from src.contracts import RunTerminalStreamPayload
from src.contracts import Session
from src.contracts import SessionMessage
from src.contracts import SessionMessageRole
from src.contracts import SessionMessagesResponse
from src.contracts import SessionStatus
from src.contracts.runtime import TextContentBlock

NOW = datetime(2026, 5, 28, 12, tzinfo=UTC)


def _session_message(sequence: int) -> SessionMessage:
    return SessionMessage(
        message_id=f"message-{sequence}",
        session_id="session-1",
        agent_run_id="agent-run-1",
        sequence=sequence,
        role=SessionMessageRole.USER,
        content=[TextContentBlock(text=f"hello-{sequence}")],
        created_at=NOW,
        updated_at=NOW,
    )


def _agent_run(**changes: object) -> AgentRun:
    values: dict[str, object] = {
        "agent_run_id": "agent-run-1",
        "session_id": "session-1",
        "input_message_id": "message-1",
        "status": AgentRunStatus.RUNNING,
        "mode": AgentMode.CHAT,
        "active_pattern": "single_turn",
        "context_message_sequence": 1,
        "trace_id": "trace-1",
        "max_steps": 12,
        "timeout_seconds": 120,
        "retry_limit": 1,
        "created_at": NOW,
        "updated_at": NOW,
        "started_at": NOW,
    }
    values.update(changes)
    return AgentRun.model_validate(values)


class TestSessionContracts:
    def test_session_and_visible_message_history_serialize(self) -> None:
        session = Session(
            session_id="session-1",
            status=SessionStatus.ACTIVE,
            title="demo",
            last_message_sequence=1,
            created_at=NOW,
            updated_at=NOW,
        )
        response = SessionMessagesResponse(
            session_id=session.session_id,
            messages=[_session_message(1)],
        )

        serialized = response.model_dump(mode="json")

        assert session.status == SessionStatus.ACTIVE
        assert serialized["messages"][0]["agent_run_id"] == "agent-run-1"
        assert serialized["messages"][0]["content"][0] == {
            "kind": "text",
            "text": "hello-1",
        }

    def test_session_messages_must_be_ordered(self) -> None:
        with pytest.raises(ValidationError, match="sequence 升序"):
            SessionMessagesResponse(
                session_id="session-1",
                messages=[_session_message(2), _session_message(1)],
            )

    def test_create_session_request_rejects_unknown_fields(self) -> None:
        with pytest.raises(ValidationError, match="extra"):
            CreateSessionRequest.model_validate({"title": "demo", "task_id": "legacy"})


class TestAgentRunContracts:
    def test_agent_run_uses_agent_run_id_and_runtime_limits(self) -> None:
        run = _agent_run()

        assert run.agent_run_id == "agent-run-1"
        assert run.mode == AgentMode.CHAT
        assert run.active_pattern == "single_turn"

    def test_terminal_run_requires_finish_reason(self) -> None:
        with pytest.raises(ValidationError, match="finish_reason"):
            _agent_run(status=AgentRunStatus.COMPLETED)

    def test_non_failed_run_rejects_error_type(self) -> None:
        with pytest.raises(ValidationError, match="仅 failed"):
            _agent_run(
                status=AgentRunStatus.CANCELLED,
                finish_reason=AgentRunFinishReason.CANCELLED,
                error_type="ModelTimeoutError",
            )

    def test_step_records_pattern_and_invocation(self) -> None:
        step = AgentRunStep(
            step_id="step-1",
            agent_run_id="agent-run-1",
            sequence=1,
            kind=AgentRunStepKind.MODEL,
            status=AgentRunStepStatus.SUCCEEDED,
            pattern="single_turn",
            invocation_id="invoke-1",
            safe_input={"visibility": "public_output"},
            created_at=NOW,
            updated_at=NOW,
            completed_at=NOW,
        )

        assert step.agent_run_id == "agent-run-1"
        assert step.safe_input == {"visibility": "public_output"}

    def test_create_agent_run_request_contains_mode_pattern_and_stream(self) -> None:
        request = CreateAgentRunRequest(
            session_id="session-1",
            input="build it",
            mode=AgentMode.BUILD,
            requested_pattern="react",
            stream=True,
        )

        assert request.mode == AgentMode.BUILD
        assert request.requested_pattern == "react"
        assert request.stream is True


class TestAgentRunStreamContracts:
    def test_stream_started_and_delta_payloads_are_typed(self) -> None:
        started = AgentRunStreamEvent(
            event="run.started",
            payload=RunStartedStreamPayload(
                agent_run_id="agent-run-1",
                session_id="session-1",
                mode=AgentMode.CHAT,
                pattern="single_turn",
                trace_id="trace-1",
            ),
        )
        delta = AgentRunStreamEvent(
            event="output.text.delta",
            payload=OutputTextDeltaStreamPayload(
                agent_run_id="agent-run-1",
                sequence=1,
                delta="hello",
            ),
        )

        assert started.model_dump(mode="json")["event"] == "run.started"
        assert delta.payload.delta == "hello"

    def test_terminal_event_must_match_status(self) -> None:
        with pytest.raises(ValidationError, match="status 不匹配"):
            AgentRunStreamEvent(
                event="run.completed",
                payload=RunTerminalStreamPayload(
                    agent_run_id="agent-run-1",
                    status="failed",
                    finish_reason=AgentRunFinishReason.ERROR,
                    error_type="ModelTimeoutError",
                ),
            )

    def test_failed_terminal_event_requires_error_type(self) -> None:
        with pytest.raises(ValidationError, match="error_type"):
            RunTerminalStreamPayload(
                agent_run_id="agent-run-1",
                status="failed",
                finish_reason=AgentRunFinishReason.ERROR,
            )
