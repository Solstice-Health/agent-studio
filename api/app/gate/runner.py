from __future__ import annotations

import logging

from sqlalchemy import delete, select

from ..models import CheckResult, Draft, Source
from . import checks

logger = logging.getLogger(__name__)

# The checks the gate runs. Add new ones here.
GATE_CHECKS = {
    "required_disclaimer": checks.required_disclaimer,
    "length_budget": checks.length_budget,
    "sections_well_formed": checks.sections_well_formed,
    "claims_supported": checks.claims_supported,
}

# A draft ships only if nothing failed and nothing errored. "errored" blocks because a
# check that could not run has vouched for nothing; see checks.claims_supported for why
# "uncertain" does not.
BLOCKING_STATUSES = {"failed", "errored"}


async def run_gate(session, run, llm=None):
    """Run every check over the run's draft, record the results, and set the draft's
    gate_status."""
    draft = (
        await session.execute(select(Draft).where(Draft.run_id == run.id))
    ).scalar_one_or_none()
    if draft is None:
        logger.info("gate skipped: run %s has no draft yet", run.id)
        return None

    source_rows = (
        await session.execute(select(Source).where(Source.run_id == run.id))
    ).scalars().all()
    sources = [{"id": s.id, "title": s.title, "text": s.text} for s in source_rows]

    # The gate is re-runnable from the UI. Without this, a second run appends a second set
    # of rows and readers silently see whichever one they iterate onto last.
    await session.execute(delete(CheckResult).where(CheckResult.draft_id == draft.id))

    blocked = False
    for key, fn in GATE_CHECKS.items():
        try:
            status, detail = await fn(draft, sources, llm)
        except Exception as exc:  # noqa: BLE001 - one broken check must not 500 the gate
            logger.exception("gate check %s errored on draft %s", key, draft.id)
            status, detail = "errored", f"{type(exc).__name__}: {exc}"
        logger.info("gate check %s on draft %s: %s %s", key, draft.id, status, detail)
        session.add(
            CheckResult(draft_id=draft.id, check_key=key, status=status, detail=detail)
        )
        if status in BLOCKING_STATUSES:
            blocked = True

    draft.gate_status = "blocked" if blocked else "accepted"
    logger.info("gate on draft %s: %s", draft.id, draft.gate_status)
    await session.flush()
    return draft
