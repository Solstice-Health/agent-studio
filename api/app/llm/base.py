from __future__ import annotations

from typing import Literal, Protocol, TypedDict, runtime_checkable


class ToolCall(TypedDict):
    id: str
    name: str
    arguments: dict


class ToolSpec(TypedDict):
    name: str
    description: str
    parameters: dict


class Message(TypedDict, total=False):
    role: str  # system | user | assistant | tool
    content: str
    tool_calls: list[ToolCall]  # on assistant turns that call tools
    tool_call_id: str  # on tool-result messages
    # The provider's own content blocks for an assistant turn, carried opaquely so the
    # next request can replay the turn byte-for-byte. Only the client that produced it
    # reads it; the engine and the gate never look inside.
    provider_content: list[dict]


class Completion(TypedDict, total=False):
    kind: Literal["final", "tool_calls"]
    text: str
    tool_calls: list[ToolCall]
    provider_content: list[dict]


@runtime_checkable
class LLMClient(Protocol):
    async def complete(self, messages: list[Message], tools: list[ToolSpec]) -> Completion: ...
