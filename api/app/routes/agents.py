from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from ..db import get_session
from ..middleware import get_current_user, get_workspace
from ..models import Agent
from ..tools.registry import TOOL_SPECS

router = APIRouter(prefix="/agents", tags=["agents"])

VALID_TOOL_KEYS = {spec["name"] for spec in TOOL_SPECS}


class AgentCreate(BaseModel):
    name: str
    system_prompt: str = ""
    tool_keys: list[str] = []


class AgentOut(BaseModel):
    id: int
    name: str
    system_prompt: str
    tool_keys: list[str]


@router.get("", response_model=list[AgentOut])
async def list_agents(workspace=Depends(get_workspace), session=Depends(get_session)):
    rows = (
        await session.execute(select(Agent).where(Agent.workspace_id == workspace.id))
    ).scalars().all()
    return [
        AgentOut(id=a.id, name=a.name, system_prompt=a.system_prompt, tool_keys=a.tool_keys or [])
        for a in rows
    ]


@router.post("", response_model=AgentOut)
async def create_agent(
    body: AgentCreate,
    user=Depends(get_current_user),
    workspace=Depends(get_workspace),
    session=Depends(get_session),
):
    unknown = sorted(set(body.tool_keys) - VALID_TOOL_KEYS)
    if unknown:
        raise HTTPException(
            status_code=400,
            detail=f"unknown tool_keys: {', '.join(unknown)}. Known: {', '.join(sorted(VALID_TOOL_KEYS))}",
        )
    agent = Agent(
        workspace_id=workspace.id,
        name=body.name,
        system_prompt=body.system_prompt,
        tool_keys=body.tool_keys,
        created_by=user.id,
    )
    session.add(agent)
    await session.commit()
    return AgentOut(
        id=agent.id, name=agent.name, system_prompt=agent.system_prompt, tool_keys=agent.tool_keys or []
    )
