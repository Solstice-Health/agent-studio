from __future__ import annotations

import os

from .base import Completion, Message, ToolSpec


class AnthropicLLM:
    """The model client the agent runs on.

    This is the real path. The agent drafts and judges by calling a live model through
    this adapter, so the product does not run until you implement complete(). Wiring it
    up is one of the core tasks.

    The tests do not use this. They inject ScriptedLLM, a deterministic stand-in, so the
    run engine can be exercised with no key and no network. This client is what an actual
    run uses.

    Point complete() at a provider (Anthropic by default, or your choice). Read the key
    from the environment so it never lands in the code or a commit.
    """

    def __init__(self, api_key: str | None = None, model: str = "claude-sonnet-4-6"):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.model = model

    async def complete(self, messages: list[Message], tools: list[ToolSpec]) -> Completion:
        # TODO: call the provider here. Translate `messages` and `tools` into the
        # provider's request, send it, and return a Completion: either
        # {"kind": "tool_calls", "tool_calls": [...]} when the model wants to use tools,
        # or {"kind": "final", "text": ...} when it is done.
        raise NotImplementedError("implement the model client: the agent runs on this")
