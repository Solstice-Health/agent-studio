from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select

from ..db import SessionLocal, get_session
from ..engine.loop import record_error, start_run
from ..fixtures import create_halo_run
from ..llm import AnthropicLLM
from ..middleware import get_current_user, get_workspace, load_run_for_workspace
from ..models import Agent, Draft, Run, RunStep

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/runs", tags=["runs"])


class RunCreate(BaseModel):
    agent_id: int


async def _run_in_background(run_id: int) -> None:
    """Drive one run to completion. The agent runs on a real model, so this needs
    ANTHROPIC_API_KEY in the environment; the tests drive the engine with the scripted
    double instead."""
    async with SessionLocal() as session:
        run = await session.get(Run, run_id)
        if run is None:
            logger.error("run %s disappeared before it could start", run_id)
            return
        try:
            await start_run(session, run, AnthropicLLM())
        except Exception as exc:  # noqa: BLE001 - a background task has nowhere to raise
            logger.exception("run %s failed", run_id)
            # The session may be poisoned if the failure came from the database, so roll
            # back before writing the failure down.
            await session.rollback()
            await _mark_failed(session, run_id, f"{type(exc).__name__}: {exc}")


async def _mark_failed(session, run_id: int, detail: str) -> None:
    run = await session.get(Run, run_id)
    if run is None:
        return
    run.status = "failed"
    await record_error(session, run, detail)


@router.post("")
async def create_run(
    body: RunCreate,
    background: BackgroundTasks,
    user=Depends(get_current_user),
    workspace=Depends(get_workspace),
    session=Depends(get_session),
):
    agent = (
        await session.execute(
            select(Agent).where(Agent.id == body.agent_id, Agent.workspace_id == workspace.id)
        )
    ).scalar_one_or_none()
    if agent is None:
        raise HTTPException(status_code=404, detail="agent not found")
    run = await create_halo_run(session, workspace, agent, user)
    await session.commit()
    logger.info("run %s queued for workspace %s by %s", run.id, workspace.slug, user.email)
    background.add_task(_run_in_background, run.id)
    return {"id": run.id, "status": run.status}


@router.get("")
async def list_runs(workspace=Depends(get_workspace), session=Depends(get_session)):
    runs = (
        await session.execute(
            select(Run).where(Run.workspace_id == workspace.id).order_by(Run.id)
        )
    ).scalars().all()
    return [{"id": r.id, "status": r.status, "brief": r.brief} for r in runs]


@router.get("/{run_id}")
async def get_run(run_id: int, workspace=Depends(get_workspace), session=Depends(get_session)):
    run = await load_run_for_workspace(session, run_id, workspace)
    draft = (
        await session.execute(select(Draft).where(Draft.run_id == run.id))
    ).scalar_one_or_none()
    return {
        "id": run.id,
        "status": run.status,
        "brief": run.brief,
        "step_count": run.step_count,
        "draft": {"sections": draft.sections, "gate_status": draft.gate_status} if draft else None,
    }


@router.get("/{run_id}/trace")
async def get_trace(run_id: int, workspace=Depends(get_workspace), session=Depends(get_session)):
    await load_run_for_workspace(session, run_id, workspace)
    steps = (
        await session.execute(
            select(RunStep).where(RunStep.run_id == run_id).order_by(RunStep.seq)
        )
    ).scalars().all()
    return {
        "run_id": run_id,
        "steps": [
            {"seq": s.seq, "kind": s.kind, "payload": s.payload, "tool_call_id": s.tool_call_id}
            for s in steps
        ],
    }


def _sse(obj: dict) -> str:
    return f"data: {json.dumps(obj)}\n\n"


@router.get("/{run_id}/stream")
async def stream_run(run_id: int):
    # EventSource cannot set custom headers, so the run view streams by id alone.
    async def gen():
        last_seq = 0
        for _ in range(240):  # ~120s cap so the stream cannot hang open forever
            async with SessionLocal() as session:
                run = await session.get(Run, run_id)
                if run is None:
                    yield _sse({"event": "error", "detail": "run not found"})
                    return
                steps = (
                    await session.execute(
                        select(RunStep)
                        .where(RunStep.run_id == run_id, RunStep.seq >= last_seq)
                        .order_by(RunStep.seq)
                    )
                ).scalars().all()
                for st in steps:
                    yield _sse({"event": "step", "seq": st.seq, "kind": st.kind, "payload": st.payload})
                    last_seq = st.seq + 1
                if run.status in ("completed", "failed", "cancelled"):
                    yield _sse({"event": "done", "status": run.status})
                    return
            await asyncio.sleep(0.5)

    return StreamingResponse(gen(), media_type="text/event-stream")
