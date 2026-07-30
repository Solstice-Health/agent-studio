from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from ..db import get_session
from ..llm import AnthropicLLM
from ..gate.runner import run_gate
from ..middleware import get_workspace, load_run_for_workspace
from ..models import CheckResult

router = APIRouter(tags=["gate"])


@router.post("/runs/{run_id}/gate")
async def run_gate_route(run_id: int, workspace=Depends(get_workspace), session=Depends(get_session)):
    run = await load_run_for_workspace(session, run_id, workspace)
    # The rule checks ignore the model; it is here for any check that wants one.
    draft = await run_gate(session, run, AnthropicLLM())
    if draft is None:
        raise HTTPException(status_code=400, detail="run has no draft yet")
    await session.commit()
    results = (
        await session.execute(select(CheckResult).where(CheckResult.draft_id == draft.id))
    ).scalars().all()
    return {
        "gate_status": draft.gate_status,
        "checks": [{"key": c.check_key, "status": c.status, "detail": c.detail} for c in results],
    }
