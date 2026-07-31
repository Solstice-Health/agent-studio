from __future__ import annotations

import json
import logging

from sqlalchemy import func, select

from ..models import Agent, RunStep
from ..tools.registry import TOOLS, ToolContext, tool_specs_for

logger = logging.getLogger(__name__)

# Upper bound on model turns, so a runaway agent cannot loop forever.
MAX_STEPS = 24


def compose_system_prompt(agent: Agent | None) -> str:
    if agent is not None and agent.system_prompt:
        return agent.system_prompt
    return "You are a content drafting agent. Read the sources and assemble a cited draft."


def _assistant_message(completion: dict) -> dict:
    message: dict = {"role": "assistant", "content": completion.get("text", "")}
    if completion.get("kind") == "tool_calls":
        message["tool_calls"] = completion.get("tool_calls", [])
    if completion.get("provider_content"):
        message["provider_content"] = completion["provider_content"]
    return message


async def execute_tool(session, run, tool_call: dict) -> dict:
    """Run one tool. An exception is isolated and handed back to the agent as an error
    result, so one bad tool call does not take down the run."""
    fn = TOOLS.get(tool_call["name"])
    if fn is None:
        return {"error": f"unknown tool: {tool_call['name']}"}
    ctx = ToolContext(session=session, run=run)
    try:
        return await fn(tool_call.get("arguments", {}), ctx)
    except Exception as exc:  # noqa: BLE001 - intentional: isolate a throwing tool
        return {"error": f"{type(exc).__name__}: {exc}"}


_KIND_BY_ROLE = {
    "system": "model_turn",
    "user": "user_input",
    "assistant": "model_turn",
    "tool": "tool_result",
}


async def record_error(session, run, detail: str) -> None:
    """Append an `error` entry to the transcript. A run that fails has to say why in the
    record the UI reads, not only in the server log."""
    seq = (
        await session.execute(
            select(func.max(RunStep.seq)).where(RunStep.run_id == run.id)
        )
    ).scalar()
    session.add(
        RunStep(run_id=run.id, seq=(seq if seq is not None else -1) + 1, kind="error",
                payload={"role": "error", "content": detail})
    )
    await session.commit()


async def _record(session, run, seq: int, message: dict) -> None:
    """Append one transcript entry to the database and commit. The commit is what lets
    /runs/{id}/stream, which polls on its own session, watch a run progress."""
    session.add(
        RunStep(
            run_id=run.id,
            seq=seq,
            kind=_KIND_BY_ROLE.get(message.get("role"), "model_turn"),
            payload=message,
            tool_call_id=message.get("tool_call_id"),
        )
    )
    await session.commit()


async def start_run(session, run, llm):
    agent = await session.get(Agent, run.agent_id)
    run.status = "running"

    transcript = [
        {"role": "system", "content": compose_system_prompt(agent)},
        {"role": "user", "content": run.brief},
    ]
    for seq, message in enumerate(transcript):
        await _record(session, run, seq, message)

    specs = tool_specs_for(agent.tool_keys if agent else None)
    logger.info(
        "run %s started: agent=%s tools=%s",
        run.id, run.agent_id, [spec["name"] for spec in specs],
    )

    while True:
        if run.step_count >= MAX_STEPS:
            run.status = "failed"
            logger.warning("run %s hit the %d-step budget without finalizing", run.id, MAX_STEPS)
            await record_error(session, run, f"step budget of {MAX_STEPS} model turns exhausted")
            break

        completion = await llm.complete(transcript, specs)
        run.step_count += 1
        message = _assistant_message(completion)
        transcript.append(message)
        await _record(session, run, len(transcript) - 1, message)

        if completion.get("kind") != "tool_calls":
            run.status = "completed"
            logger.info("run %s completed after %d model turns", run.id, run.step_count)
            break

        for tool_call in completion.get("tool_calls", []):
            result = await execute_tool(session, run, tool_call)
            if "error" in result:
                logger.warning(
                    "run %s tool %s failed: %s", run.id, tool_call["name"], result["error"]
                )
            else:
                logger.info("run %s tool %s ok", run.id, tool_call["name"])
            message = {
                "role": "tool",
                "tool_call_id": tool_call.get("id"),
                "content": json.dumps(result),
            }
            transcript.append(message)
            await _record(session, run, len(transcript) - 1, message)

    await session.commit()
    return run
