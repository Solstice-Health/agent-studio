from __future__ import annotations

from sqlalchemy import select

from ..models import CheckResult, Draft, Source
from . import checks

# The checks the gate runs. Add new ones here.
GATE_CHECKS = {
    "required_disclaimer": checks.required_disclaimer,
    "length_budget": checks.length_budget,
    "sections_well_formed": checks.sections_well_formed,
}


async def run_gate(session, run, llm=None):
    """Run every check over the run's draft, record the results, and set the draft's
    gate_status. A draft is accepted only if nothing failed."""
    draft = (
        await session.execute(select(Draft).where(Draft.run_id == run.id))
    ).scalar_one_or_none()
    if draft is None:
        return None

    source_rows = (
        await session.execute(select(Source).where(Source.run_id == run.id))
    ).scalars().all()
    sources = [{"id": s.id, "title": s.title, "text": s.text} for s in source_rows]

    blocked = False
    for key, fn in GATE_CHECKS.items():
        status, detail = await fn(draft, sources, llm)
        session.add(
            CheckResult(draft_id=draft.id, check_key=key, status=status, detail=detail)
        )
        if status == "failed":
            blocked = True

    draft.gate_status = "blocked" if blocked else "accepted"
    await session.flush()
    return draft
