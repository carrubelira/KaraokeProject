"""What the server is: its version, its certificate's fingerprint, its clock; and lyrics search."""

import asyncio
from dataclasses import asdict
from importlib import metadata
from typing import Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from karaoke_server.auth import Operator, operator
from karaoke_server.clock import now_us
from karaoke_server.errors import ApiError
from karaoke_server.routes._deps import services

router = APIRouter(prefix="/api", tags=["server"])


class ServerInfo(BaseModel):
    version: str
    fingerprint: str
    now: int
    tls: bool


@router.get("/server")
async def info(request: Request) -> ServerInfo:
    found = services(request)
    return ServerInfo(
        version=metadata.version("karaoke-server"),
        fingerprint=found.fingerprint,
        now=now_us(),
        tls=found.settings.tls,
    )


@router.get("/lyrics/search")
async def search_lyrics(
    request: Request, q: str, duration: float | None = None, who: Operator = Depends(operator)
) -> list[dict[str, Any]]:
    """LRCLIB candidates for the operator to pick from: duration gap and whether it has times."""
    from karaoke_engine.lyrics_lookup import search_lyrics as search

    fetch = getattr(request.app.state, "lrclib_fetch", None)
    try:
        found = await asyncio.to_thread(search, q, duration, fetch)
    except OSError as exc:
        raise ApiError(502, "lrclib_unavailable", str(exc)) from exc
    return [asdict(c) for c in found]
