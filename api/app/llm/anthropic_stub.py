from __future__ import annotations

from .base import Completion, Message, ToolSpec


class AnthropicLLM:
    """Optional real-model client, for your own demo only. Fill it in with your own
    key if you want to watch a run against a live model. Tests and grading use
    ScriptedLLM, so nothing should depend on this working."""

    def __init__(self, api_key: str | None = None, model: str = "claude-opus-4-1"):
        self.api_key = api_key
        self.model = model

    async def complete(self, messages: list[Message], tools: list[ToolSpec]) -> Completion:
        raise NotImplementedError("wire up the Anthropic API here with your own key")
