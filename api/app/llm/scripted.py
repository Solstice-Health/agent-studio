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
    """A deterministic stand-in for a model provider, used by the tests and the seed.

    It has two modes, chosen by whether the caller passes tools:

    - Agent loop (tools given): returns the next scripted step for the run. The
      script is matched by a marker that appears in the brief, and the step index
      is the number of assistant turns already in the transcript.
    - Evaluation (no tools): returns a scripted verdict as JSON in ``text``, matched
      by a phrase in the content under review. Shape:
      ``{"supported": bool | null, "reason": str}``. ``null`` means the model is not sure.

    Because it answers from the input rather than a fixed queue, you can design the
    agent loop and any model-backed check however you like and it will still respond.
    """

    def __init__(self, scripts: dict[str, list[Completion]], verdicts: dict[str, dict]):
        self.scripts = scripts
        self.verdicts = verdicts

    async def complete(self, messages: list[Message], tools: list[ToolSpec]) -> Completion:
        blob = _blob(messages)
        if tools:
            script = self._match_script(blob)
            idx = sum(1 for m in messages if m.get("role") == "assistant")
            if idx >= len(script):
                return {"kind": "final", "text": "Draft complete."}
            return script[idx]
        # Evaluation call.
        for marker, verdict in self.verdicts.items():
            if marker.lower() in blob:
                return {"kind": "final", "text": json.dumps(verdict)}
        return {"kind": "final", "text": json.dumps({"supported": True, "reason": "no issue found"})}

    def _match_script(self, blob: str) -> list[Completion]:
        for marker, script in self.scripts.items():
            if marker.lower() in blob:
                return script
        return [{"kind": "final", "text": "Draft complete."}]
