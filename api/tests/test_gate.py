from sqlalchemy import select

from app.engine.loop import start_run
from app.fixtures import create_halo_run, make_scripted_llm
from app.gate.runner import GATE_CHECKS, run_gate
from app.models import Agent, CheckResult, Draft, User, Workspace


async def _run_halo(session):
    ws = Workspace(slug="acme", name="Acme")
    session.add(ws)
    await session.flush()
    user = User(workspace_id=ws.id, email="creator@acme.test", role="member")
    session.add(user)
    await session.flush()
    agent = Agent(
        workspace_id=ws.id,
        name="Drafting agent",
        system_prompt="",
        tool_keys=["list_sources", "get_source", "add_section"],
        created_by=user.id,
    )
    session.add(agent)
    await session.flush()
    run = await create_halo_run(session, ws, agent, user)
    await start_run(session, run, make_scripted_llm())
    return run


async def _check_results(session, draft):
    results = (
        await session.execute(select(CheckResult).where(CheckResult.draft_id == draft.id))
    ).scalars().all()
    return {r.check_key: (r.status, r.detail) for r in results}


async def test_rule_checks_pass_on_clean_draft(session):
    run = await _run_halo(session)
    draft = await run_gate(session, run, make_scripted_llm())
    assert draft is not None
    by_key = await _check_results(session, draft)
    assert by_key["required_disclaimer"][0] == "passed"
    assert by_key["length_budget"][0] == "passed"
    assert by_key["sections_well_formed"][0] == "passed"


async def test_gate_is_rerunnable_without_duplicating_results(session):
    run = await _run_halo(session)
    draft = await run_gate(session, run, make_scripted_llm())
    await run_gate(session, run, make_scripted_llm())
    results = (
        await session.execute(select(CheckResult).where(CheckResult.draft_id == draft.id))
    ).scalars().all()
    assert len(results) == len(GATE_CHECKS)


# --- the claim-support check (your task) ---
#
# These two fail until verify_claim_support is implemented. The check and its wiring into
# the gate are done; both tests exercise it through the gate.


async def test_gate_blocks_draft_with_unsupported_claim(session):
    # The Halo draft claims "Clinically proven sleep tracking", which an internal
    # 200-person study does not back.
    run = await _run_halo(session)
    draft = await run_gate(session, run, make_scripted_llm())
    assert draft.gate_status == "blocked"
    status, detail = (await _check_results(session, draft))["claims_supported"]
    assert status == "failed"
    assert "clinically proven" in detail.lower()


async def test_gate_passes_faithful_paraphrase(session):
    # "Keeps going for more than a day on a single charge" is a faithful paraphrase of the
    # 30-hour spec, so a draft whose only claim is that paraphrase is accepted.
    run = await _run_halo(session)
    draft = (
        await session.execute(select(Draft).where(Draft.run_id == run.id))
    ).scalar_one()
    draft.sections = [
        s for s in draft.sections if s["title"] in ("Built for daily life", "The fine print")
    ]
    await session.flush()

    draft = await run_gate(session, run, make_scripted_llm())
    assert (await _check_results(session, draft))["claims_supported"][0] == "passed"
    assert draft.gate_status == "accepted"
