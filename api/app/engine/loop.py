from __future__ import annotations

import json

from ..models import Agent, RunStep
from ..tools.registry import TOOLS, ToolContext, tool_specs_for

# Working transcript for each in-flight run, held in memory while it executes.
_TRANSCRIPTS: dict[int, list] = {}


def compose_system_prompt(agent: Agent | None) -> str:
    if agent is not None and agent.system_prompt:
        return agent.system_prompt
    return "You are a content drafting agent. Read the sources and assemble a cited draft."


def _assistant_message(completion: dict) -> dict:
    if completion.get("kind") == "tool_calls":
        return {"role": "assistant", "content": "", "tool_calls": completion.get("tool_calls", [])}
    return {"role": "assistant", "content": completion.get("text", "")}


async def execute_tool(session, run, tool_call: dict) -> dict:
    fn = TOOLS.get(tool_call["name"])
    if fn is None:
        return {"error": f"unknown tool: {tool_call['name']}"}
    ctx = ToolContext(session=session, run=run)
    return await fn(tool_call.get("arguments", {}), ctx)


async def start_run(session, run, llm):
    agent = await session.get(Agent, run.agent_id)
    run.status = "running"
    await session.flush()

    transcript = [
        {"role": "system", "content": compose_system_prompt(agent)},
        {"role": "user", "content": run.brief},
    ]
    _TRANSCRIPTS[run.id] = transcript
    specs = tool_specs_for(agent.tool_keys if agent else None)

    while True:
        completion = await llm.complete(transcript, specs)
        transcript.append(_assistant_message(completion))
        run.step_count += 1
        if completion.get("kind") != "tool_calls":
            break
        for tc in completion.get("tool_calls", []):
            result = await execute_tool(session, run, tc)
            transcript.append(
                {"role": "tool", "tool_call_id": tc.get("id"), "content": json.dumps(result)}
            )

    await _flush_transcript(session, run, transcript)
    run.status = "completed"
    await session.commit()
    return run


_KIND_BY_ROLE = {
    "system": "model_turn",
    "user": "user_input",
    "assistant": "model_turn",
    "tool": "tool_result",
}


async def _flush_transcript(session, run, transcript) -> None:
    for i, m in enumerate(transcript):
        session.add(
            RunStep(
                run_id=run.id,
                seq=i,
                kind=_KIND_BY_ROLE.get(m.get("role"), "model_turn"),
                payload=m,
                tool_call_id=m.get("tool_call_id"),
            )
        )
    await session.flush()


async def resume_run(session, run, llm):
    # TODO: not implemented.
    raise NotImplementedError("resume is not implemented")
