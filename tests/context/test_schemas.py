"""上下文 schema 测试。"""

from src.context import ContextBundle
from src.context import ContextConversionError
from src.context import ContextItem
from src.context import ContextItemType
from src.context import ContextSource
from src.contracts.runtime import ModelMessage
from src.contracts.runtime import ModelRole
from src.contracts.runtime import TextContentBlock


def _message(text: str) -> ModelMessage:
    return ModelMessage(role=ModelRole.USER, content=[TextContentBlock(text=text)])


def test_session_item_requires_model_message_content() -> None:
    """session item 必须承载已转换的 ModelMessage。"""
    item = ContextItem(
        source=ContextSource.SESSION,
        type=ContextItemType.MESSAGE,
        content=_message("hello"),
        metadata={"sequence": 1},
    )

    assert item.source == ContextSource.SESSION
    assert item.sequence == 1


def test_context_item_rejects_sensitive_metadata() -> None:
    """ContextItem metadata 不允许包含敏感字段。"""
    try:
        ContextItem(
            source=ContextSource.SESSION,
            type=ContextItemType.MESSAGE,
            content=_message("hello"),
            metadata={"sequence": 1, "authorization": "Bearer secret"},
        )
    except ValueError as exc:
        assert "敏感字段" in str(exc)
    else:
        raise AssertionError("ContextItem 应拒绝敏感 metadata")


def test_bundle_to_model_messages_preserves_sequence_order() -> None:
    """ContextBundle 模型消息视图按 sequence 升序输出。"""
    bundle = ContextBundle(
        agent_run_id="run-1",
        session_id="session-1",
        session_messages=[
            ContextItem(
                source=ContextSource.SESSION,
                type=ContextItemType.MESSAGE,
                content=_message("second"),
                metadata={"sequence": 2},
            ),
            ContextItem(
                source=ContextSource.SESSION,
                type=ContextItemType.MESSAGE,
                content=_message("first"),
                metadata={"sequence": 1},
            ),
        ],
    )

    assert [block.text for message in bundle.to_model_messages() for block in message.content] == [
        "first",
        "second",
    ]


def test_bundle_to_model_messages_rejects_non_message_item() -> None:
    """session_messages 中不可转换的 item 会产生上下文转换错误。"""
    bundle = ContextBundle(
        agent_run_id="run-1",
        session_id="session-1",
        session_messages=[
            ContextItem(
                source=ContextSource.MEMORY,
                type=ContextItemType.SUMMARY,
                content={"summary": "old context"},
                metadata={},
            )
        ],
    )

    try:
        bundle.to_model_messages()
    except ContextConversionError:
        return
    raise AssertionError("不可转换 item 应触发 ContextConversionError")
