from sqlalchemy import select

from app.engine.loop import MAX_STEPS, start_run
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


async def test_run_stops_at_step_budget(session):
    from app.fixtures import NEVER_FINALIZE_BRIEF

    ws, user, agent = await _setup(session)
    run = await create_halo_run(session, ws, agent, user)
    run.brief = NEVER_FINALIZE_BRIEF
    await session.flush()
    await start_run(session, run, make_scripted_llm())
    assert run.step_count == MAX_STEPS
    assert run.status == "failed"


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


async def test_cannot_read_run_from_other_workspace(client, sessionmaker_, seed):
    def h(slug):
        return {"X-Workspace-Slug": slug, "X-User-Email": f"creator@{slug}.test"}

    await seed("acme", with_agent=True)
    globex = await seed("globex", with_agent=True)
    async with sessionmaker_() as s:
        ws = await s.get(Workspace, globex["workspace_id"])
        agent = await s.get(Agent, globex["agent_id"])
        run = await create_halo_run(s, ws, agent)
        await s.commit()
        run_id = run.id

    # The owner still reads it, so the boundary is scoping and not a blanket 404.
    assert (await client.get(f"/runs/{run_id}", headers=h("globex"))).status_code == 200

    for path in (f"/runs/{run_id}", f"/runs/{run_id}/trace"):
        assert (await client.get(path, headers=h("acme"))).status_code in (403, 404)
    blocked = await client.post(f"/runs/{run_id}/gate", headers=h("acme"))
    assert blocked.status_code in (403, 404)
