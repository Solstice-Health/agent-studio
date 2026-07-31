from __future__ import annotations

import logging

from .config import LOG_LEVEL

_FORMAT = "%(asctime)s %(levelname)-8s %(name)-22s %(message)s"


def setup_logging() -> None:
    # force=True because uvicorn installs its own root handler before the app's
    # lifespan runs; without it every app log line is swallowed.
    logging.basicConfig(level=LOG_LEVEL, format=_FORMAT, force=True)
    # The SDK logs every request body at DEBUG, which drowns the transcript.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("anthropic").setLevel(logging.INFO)
