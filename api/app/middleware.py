"""The auth shim. No passwords or tokens: two request headers resolve a workspace
and a user. Documented in api/README.md. Candidates should not need to touch this."""

from fastapi import Depends, Header, HTTPException
from sqlalchemy import select

from .db import get_session
from .models import User, Workspace


async def get_workspace(
    x_workspace_slug: str | None = Header(default=None),
    session=Depends(get_session),
) -> Workspace:
    if not x_workspace_slug:
        raise HTTPException(status_code=400, detail="Missing X-Workspace-Slug header")
    ws = (
        await session.execute(select(Workspace).where(Workspace.slug == x_workspace_slug))
    ).scalar_one_or_none()
    if ws is None:
        raise HTTPException(status_code=404, detail="Unknown workspace")
    return ws


async def get_current_user(
    x_user_email: str | None = Header(default=None),
    workspace: Workspace = Depends(get_workspace),
    session=Depends(get_session),
) -> User:
    if not x_user_email:
        raise HTTPException(status_code=400, detail="Missing X-User-Email header")
    user = (
        await session.execute(
            select(User).where(User.workspace_id == workspace.id, User.email == x_user_email)
        )
    ).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="Unknown user for this workspace")
    return user
