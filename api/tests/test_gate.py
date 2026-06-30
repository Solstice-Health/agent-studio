import pytest
from sqlalchemy import select

from app.engine.loop import start_run
from app.fixtures import create_halo_run, make_scripted_llm
from app.gate.runner import run_gate
from app.models import Agent, CheckResult, User, Workspace


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


async def test_rule_checks_pass_on_clean_draft(session):
    run = await _run_halo(session)
    draft = await run_gate(session, run, make_scripted_llm())
    assert draft is not None
    assert draft.gate_status == "accepted"
    results = (
        await session.execute(select(CheckResult).where(CheckResult.draft_id == draft.id))
    ).scalars().all()
    by_key = {r.check_key: r.status for r in results}
    assert by_key == {
        "required_disclaimer": "passed",
        "length_budget": "passed",
        "sections_well_formed": "passed",
    }


@pytest.mark.skip(reason="task 2: the claim-support check must block an unsupported claim")
async def test_gate_blocks_draft_with_unsupported_claim(session):
    # Once claims_supported is implemented and wired into the runner, the Halo draft
    # contains "Clinically proven sleep tracking", which the sources do not back, so
    # the gate should block.
    run = await _run_halo(session)
    draft = await run_gate(session, run, make_scripted_llm())
    assert draft.gate_status == "blocked"


@pytest.mark.skip(reason="task 2: a faithful paraphrase should pass the check")
async def test_gate_passes_faithful_paraphrase(session):
    # "Keeps going for more than a day on a single charge" is supported by the 30-hour
    # spec, so a draft whose only claim is that paraphrase should be accepted.
    run = await _run_halo(session)
    draft = await run_gate(session, run, make_scripted_llm())
    assert draft.gate_status in ("accepted", "blocked")
