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


class Completion(TypedDict, total=False):
    kind: Literal["final", "tool_calls"]
    text: str
    tool_calls: list[ToolCall]


@runtime_checkable
class LLMClient(Protocol):
    async def complete(self, messages: list[Message], tools: list[ToolSpec]) -> Completion: ...
