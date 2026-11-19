"""The content store over HTTP: read with Range, write with the hash checked, or by path."""

import asyncio
import hashlib
import os
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel

from karaoke_server.auth import Node, Operator, anyone, node
from karaoke_server.errors import ApiError
from karaoke_server.routes._deps import services

router = APIRouter(prefix="/api/blobs", tags=["blobs"])


def _check(sha256: str) -> None:
    if len(sha256) != 64 or any(c not in "0123456789abcdef" for c in sha256):
        raise ApiError(422, "bad_hash", "Not a SHA-256")


@router.api_route("/{sha256}", methods=["GET", "HEAD"], response_class=FileResponse)
async def read(
    sha256: str, request: Request, who: Operator | Node = Depends(anyone)
) -> FileResponse:
    """The blob's bytes; `Range` is honoured, so downloads resume. Blobs never change."""
    _check(sha256)
    store = services(request).store
    if not store.has(sha256):
        raise ApiError(404, "not_found", "No such blob")
    return FileResponse(
        store.path(sha256),
        media_type="application/octet-stream",
        headers={"Cache-Control": "private, max-age=31536000, immutable", "ETag": f'"{sha256}"'},
    )


class Stored(BaseModel):
    sha256: str
    size: int


@router.put("/{sha256}")
async def write(sha256: str, request: Request, who: Operator | Node = Depends(anyone)) -> Stored:
    """Stores the body under its hash, which must be `sha256` (a corrupt upload is refused)."""
    _check(sha256)
    found = services(request)
    if found.store.has(sha256):
        return Stored(sha256=sha256, size=found.store.path(sha256).stat().st_size)
    limit = found.settings.max_upload_bytes
    size = 0
    digest = hashlib.sha256()
    # Hashed while it streams to a temporary file in the store, then renamed into place.
    tmp = found.store.root / "tmp"
    await asyncio.to_thread(tmp.mkdir, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=tmp, delete=False) as out:
        name = out.name
        async for chunk in request.stream():
            size += len(chunk)
            if size > limit:
                break
            digest.update(chunk)
            out.write(chunk)
    if size > limit:
        await asyncio.to_thread(os.unlink, name)
        raise ApiError(413, "too_big", "The blob is too big")
    if digest.hexdigest() != sha256:
        await asyncio.to_thread(os.unlink, name)
        raise ApiError(422, "hash_mismatch", f"expected {sha256}, got {digest.hexdigest()}")
    await asyncio.to_thread(_move_into, name, found.store.path(sha256))
    return Stored(sha256=sha256, size=size)


def _move_into(name: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    os.replace(name, dest)


class LocalPath(BaseModel):
    path: str


@router.get("/{sha256}/local")
async def local(sha256: str, request: Request, who: Node = Depends(node)) -> LocalPath:
    """Where the blob is on this disk, for a node on the server's own machine."""
    _check(sha256)
    if not who.capabilities.same_host_as_server:
        raise ApiError(403, "forbidden", "Only nodes on the server's machine read by path")
    store = services(request).store
    if not store.has(sha256):
        raise ApiError(404, "not_found", "No such blob")
    return LocalPath(path=str(store.path(sha256).resolve()))


@router.get("", include_in_schema=False)
async def nothing() -> Response:
    raise ApiError(404, "not_found", "Name a blob")
