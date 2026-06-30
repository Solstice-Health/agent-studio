import pytest
from sqlalchemy import select

from app.engine.loop import start_run
from app.fixtures import create_halo_run, make_scripted_llm
from app.llm.scripted import ScriptedLLM
from app.models import Agent, Draft, User, Workspace


async def _setup(session, slug="acme"):
    ws = Workspace(slug=slug, name=slug.title())
    session.add(ws)
    await session.flush()
    user = User(workspace_id=ws.id, email=f"creator@{slug}.test", role="member")
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
    return ws, user, agent


async def test_run_produces_draft(session):
    ws, user, agent = await _setup(session)
    run = await create_halo_run(session, ws, agent, user)
    await start_run(session, run, make_scripted_llm())

    assert run.status == "completed"
    draft = (
        await session.execute(select(Draft).where(Draft.run_id == run.id))
    ).scalar_one_or_none()
    assert draft is not None
    assert len(draft.sections) == 3
    titles = [s["title"] for s in draft.sections]
    assert "Built for daily life" in titles


# --- The work. These are skipped until you build it. ---


@pytest.mark.skip(reason="task 1: enforce a step budget so a chatty agent cannot run forever")
async def test_run_stops_at_step_budget(session):
    from app.fixtures import NEVER_FINALIZE_BRIEF

    ws, user, agent = await _setup(session)
    run = await create_halo_run(session, ws, agent, user)
    run.brief = NEVER_FINALIZE_BRIEF
    await session.flush()
    await start_run(session, run, make_scripted_llm())
    assert run.step_count <= 30  # whatever budget you choose
    assert run.status in ("failed", "completed")


@pytest.mark.skip(reason="task 1: a throwing tool should be isolated, not kill the run")
async def test_throwing_tool_does_not_kill_run(session):
    ws, user, agent = await _setup(session)
    run = await create_halo_run(session, ws, agent, user)
    run.brief = "throwing fixture"
    await session.flush()
    scripts = {
        "throwing fixture": [
            {"kind": "tool_calls", "tool_calls": [{"id": "t1", "name": "fetch_reference", "arguments": {"url": "http://evil.example/x"}}]},
            {"kind": "tool_calls", "tool_calls": [{"id": "t2", "name": "add_section", "arguments": {"title": "S", "body": "Not a medical device.", "cited_source_ids": [1]}}]},
            {"kind": "final", "text": "done"},
        ]
    }
    await start_run(session, run, ScriptedLLM(scripts))
    assert run.status == "completed"


@pytest.mark.skip(reason="task 1: a run interrupted mid-step must resume cleanly, once")
async def test_interrupted_run_resumes_cleanly(session):
    from app.engine.loop import resume_run
    from app.tools import registry
    from app.tools.registry import SimulatedCrash

    ws, user, agent = await _setup(session)
    run = await create_halo_run(session, ws, agent, user)
    registry.SIMULATE_CRASH_ON_SECTION = "Built for daily life"
    try:
        with pytest.raises(SimulatedCrash):
            await start_run(session, run, make_scripted_llm())
        registry.SIMULATE_CRASH_ON_SECTION = None
        await resume_run(session, run, make_scripted_llm())
        draft = (
            await session.execute(select(Draft).where(Draft.run_id == run.id))
        ).scalar_one_or_none()
        titles = [s["title"] for s in draft.sections]
        assert titles.count("Built for daily life") == 1  # not run twice on resume
        assert run.status == "completed"
    finally:
        registry.SIMULATE_CRASH_ON_SECTION = None


@pytest.mark.skip(reason="stretch: one workspace must not be able to read another's run")
async def test_cannot_read_run_from_other_workspace(client, seed):
    def h(slug):
        return {"X-Workspace-Slug": slug, "X-User-Email": f"creator@{slug}.test"}

    acme = await seed("acme", with_agent=True)
    globex = await seed("globex", with_agent=True)
    made = await client.post("/runs", headers=h("globex"), json={"agent_id": globex["agent_id"]})
    globex_run_id = made.json()["id"]
    leaked = await client.get(f"/runs/{globex_run_id}", headers=h("acme"))
    assert leaked.status_code in (403, 404)


@pytest.mark.skip(reason="stretch: ask_user should pause and resume durably")
async def test_ask_user_pauses_persists_and_resumes(session):
    ws, user, agent = await _setup(session)
    run = await create_halo_run(session, ws, agent, user)
    run.brief = "ask fixture"
    await session.flush()
    scripts = {
        "ask fixture": [
            {"kind": "tool_calls", "tool_calls": [{"id": "a1", "name": "ask_user", "arguments": {"question": "city or metro?"}}]},
            {"kind": "final", "text": "done"},
        ]
    }
    await start_run(session, run, ScriptedLLM(scripts))
    assert run.status == "needs_input"
