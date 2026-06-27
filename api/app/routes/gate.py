from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from ..db import get_session
from ..fixtures import make_scripted_llm
from ..gate.runner import run_gate
from ..middleware import get_workspace
from ..models import CheckResult, Run

router = APIRouter(tags=["gate"])


@router.post("/runs/{run_id}/gate")
async def run_gate_route(run_id: int, workspace=Depends(get_workspace), session=Depends(get_session)):
    run = await session.get(Run, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="run not found")
    draft = await run_gate(session, run, make_scripted_llm())
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
