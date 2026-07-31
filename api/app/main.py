from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from .db import engine, init_db
from .logging import setup_logging
from .routes import agents, gate, runs

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("starting up: creating tables if needed")
    await init_db()
    logger.info("startup complete")
    yield


app = FastAPI(title="Agent Studio", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(agents.router)
app.include_router(runs.router)
app.include_router(gate.router)


@app.get("/health")
async def health():
    """Liveness plus a real database round-trip, so an api that came up while Postgres
    was unreachable reports unhealthy instead of reporting ok and failing on first use."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 - the detail is the point of the endpoint
        logger.exception("health check could not reach the database")
        return JSONResponse(
            status_code=503,
            content={"ok": False, "database": f"{type(exc).__name__}: {exc}"},
        )
    return {"ok": True, "database": "ok"}
