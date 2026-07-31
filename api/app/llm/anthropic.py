from __future__ import annotations

import logging
import os

from anthropic import AsyncAnthropic

from ..config import ANTHROPIC_MAX_TOKENS, ANTHROPIC_MODEL
from .base import Completion, Message, ToolSpec

logger = logging.getLogger(__name__)


class AnthropicLLM:
    """The model client the agent runs on.

    This is the real path: the agent drafts by calling a live model through this adapter.
    Reads ANTHROPIC_API_KEY and ANTHROPIC_MODEL from the environment.

    The tests do not use this. They inject ScriptedLLM, a deterministic stand-in, so the
    run engine can be exercised with no key and no network.

    Everything provider-shaped is confined to this file. The engine speaks the neutral
    Message/Completion shapes in llm/base.py, so swapping providers means writing a
    second class with the same one method, not touching the loop.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str = ANTHROPIC_MODEL,
        max_tokens: int = ANTHROPIC_MAX_TOKENS,
    ):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.model = model
        self.max_tokens = max_tokens
        self._client = AsyncAnthropic(api_key=self.api_key) if self.api_key else None

    async def complete(self, messages: list[Message], tools: list[ToolSpec]) -> Completion:
        if self._client is None:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set, so the agent has no model to run on. "
                "Put it in agent-studio/.env (see .env.example) and restart the api."
            )

        system, turns = _to_provider_messages(messages)
        request: dict = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": turns,
        }
        if system:
            request["system"] = system
        if tools:
            request["tools"] = [_to_provider_tool(spec) for spec in tools]

        logger.info("model request: model=%s turns=%d tools=%d", self.model, len(turns), len(tools))
        response = await self._client.messages.create(**request)
        logger.info(
            "model response: stop_reason=%s in=%d out=%d",
            response.stop_reason,
            response.usage.input_tokens,
            response.usage.output_tokens,
        )

        # Kept verbatim so the next turn replays this one exactly as the provider produced
        # it. Models that think need their thinking blocks echoed back unchanged, and
        # rebuilding the turn from text plus tool calls silently drops them.
        provider_content = [block.model_dump() for block in response.content]

        tool_calls = [
            {"id": block.id, "name": block.name, "arguments": dict(block.input or {})}
            for block in response.content
            if block.type == "tool_use"
        ]
        text = "".join(block.text for block in response.content if block.type == "text")

        if tool_calls:
            return {
                "kind": "tool_calls",
                "text": text,
                "tool_calls": tool_calls,
                "provider_content": provider_content,
            }
        return {"kind": "final", "text": text, "provider_content": provider_content}


def _to_provider_tool(spec: ToolSpec) -> dict:
    return {
        "name": spec["name"],
        "description": spec.get("description", ""),
        "input_schema": spec.get("parameters") or {"type": "object", "properties": {}},
    }


def _to_provider_messages(messages: list[Message]) -> tuple[str, list[dict]]:
    """Translate the engine's transcript into (system prompt, provider turns).

    Two shape mismatches to bridge: the system prompt is a top-level field rather than a
    turn, and tool results are user turns rather than a role of their own — consecutive
    results have to be batched into one turn, or the provider rejects an assistant turn
    whose tool_use blocks were not all answered together.
    """
    system_parts: list[str] = []
    turns: list[dict] = []

    for message in messages:
        role = message.get("role")

        if role == "system":
            if message.get("content"):
                system_parts.append(message["content"])

        elif role == "tool":
            block = {
                "type": "tool_result",
                "tool_use_id": message.get("tool_call_id"),
                "content": message.get("content", ""),
            }
            if _is_tool_result_turn(turns):
                turns[-1]["content"].append(block)
            else:
                turns.append({"role": "user", "content": [block]})

        elif role == "assistant":
            turns.append({"role": "assistant", "content": _assistant_content(message)})

        else:
            turns.append({"role": "user", "content": message.get("content", "")})

    return "\n\n".join(system_parts), turns


def _is_tool_result_turn(turns: list[dict]) -> bool:
    if not turns or turns[-1]["role"] != "user":
        return False
    content = turns[-1]["content"]
    return isinstance(content, list) and bool(content) and content[0].get("type") == "tool_result"


def _assistant_content(message: Message) -> list[dict]:
    provider_content = message.get("provider_content")
    if provider_content:
        return provider_content

    # No provider blocks: the turn came from the scripted double, so rebuild it.
    blocks: list[dict] = []
    if message.get("content"):
        blocks.append({"type": "text", "text": message["content"]})
    for call in message.get("tool_calls") or []:
        blocks.append(
            {
                "type": "tool_use",
                "id": call["id"],
                "name": call["name"],
                "input": call.get("arguments") or {},
            }
        )
    # An assistant turn may not be empty.
    return blocks or [{"type": "text", "text": "(no content)"}]
