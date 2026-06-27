from __future__ import annotations

import json

from .base import Completion, Message, ToolSpec


def _blob(messages: list[Message]) -> str:
    parts: list[str] = []
    for m in messages:
        content = m.get("content")
        if isinstance(content, str):
            parts.append(content)
        for tc in m.get("tool_calls", []) or []:
            parts.append(json.dumps(tc.get("arguments", {})))
    return "\n".join(parts).lower()


class ScriptedLLM:
    """A deterministic stand-in for a model provider, used by the tests and the seed run.

    Given a list of scripted steps per run, it returns the next step for the agent
    loop. The script is matched by a marker that appears in the brief, and the step
    index is the number of assistant turns already in the transcript, so it answers
    correctly however you structure the loop. Swap in a real client (see AnthropicLLM)
    to run against a live model.
    """

    def __init__(self, scripts: dict[str, list[Completion]]):
        self.scripts = scripts

    async def complete(self, messages: list[Message], tools: list[ToolSpec]) -> Completion:
        blob = _blob(messages)
        script = self._match_script(blob)
        idx = sum(1 for m in messages if m.get("role") == "assistant")
        if idx >= len(script):
            return {"kind": "final", "text": "Draft complete."}
        return script[idx]

    def _match_script(self, blob: str) -> list[Completion]:
        for marker, script in self.scripts.items():
            if marker.lower() in blob:
                return script
        return [{"kind": "final", "text": "Draft complete."}]
