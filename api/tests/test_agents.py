import pytest


def _h(slug="acme"):
    return {"X-Workspace-Slug": slug, "X-User-Email": f"creator@{slug}.test"}


async def test_auth_shim_resolves_user(client, seed):
    await seed("acme", with_agent=True)
    r = await client.get("/agents", headers=_h("acme"))
    assert r.status_code == 200


async def test_missing_workspace_header_is_rejected(client, seed):
    await seed("acme", with_agent=True)
    r = await client.get("/agents")
    assert r.status_code == 400


async def test_unknown_workspace_is_rejected(client, seed):
    await seed("acme", with_agent=True)
    r = await client.get(
        "/agents",
        headers={"X-Workspace-Slug": "nope", "X-User-Email": "creator@acme.test"},
    )
    assert r.status_code == 404


async def test_create_agent(client, seed):
    await seed("acme")
    r = await client.post(
        "/agents",
        headers=_h("acme"),
        json={"name": "Writer", "tool_keys": ["list_sources", "add_section"]},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["name"] == "Writer"
    assert body["id"] > 0


async def test_list_agents_is_scoped_to_workspace(client, seed):
    await seed("acme", with_agent=True)
    await seed("globex", with_agent=True)
    r = await client.get("/agents", headers=_h("acme"))
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 1


@pytest.mark.skip(reason="task: create_agent should validate tool_keys against the registry")
async def test_create_agent_rejects_unknown_tool(client, seed):
    await seed("acme")
    r = await client.post(
        "/agents",
        headers=_h("acme"),
        json={"name": "Bad", "tool_keys": ["does_not_exist"]},
    )
    assert r.status_code == 400
