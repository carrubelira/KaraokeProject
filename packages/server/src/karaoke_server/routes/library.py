"""The library: songs, their versions, their manifest and lyrics, the trash and the GC."""

from typing import Any

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel

from karaoke_contracts import Lyrics, Manifest
from karaoke_server.auth import Node, Operator, anyone, operator
from karaoke_server.errors import ApiError
from karaoke_server.routes._deps import services

router = APIRouter(prefix="/api/contents", tags=["library"])


class Content(BaseModel):
    id: str
    manifest: str
    version: int
    title: str
    artist: str | None
    language: str
    duration: float
    created_at: str
    updated_at: str
    deleted_at: str | None


@router.get("")
async def list_contents(
    request: Request, trash: bool = False, who: Operator | Node = Depends(anyone)
) -> list[Content]:
    return [Content.model_validate(c) for c in services(request).library.contents(trash=trash)]


@router.get("/{content_id}")
async def get_content(
    content_id: str, request: Request, who: Operator | Node = Depends(anyone)
) -> Content:
    return Content.model_validate(services(request).library.get(content_id))


@router.get("/{content_id}/versions")
async def versions(
    content_id: str, request: Request, who: Operator = Depends(operator)
) -> list[dict[str, Any]]:
    return services(request).library.versions(content_id)


@router.get("/{content_id}/manifest")
async def manifest(
    content_id: str,
    request: Request,
    version: str | None = None,
    who: Operator | Node = Depends(anyone),
) -> Manifest:
    library = services(request).library
    sha = version or library.get(content_id)["manifest"]
    found = library.manifest(sha)
    if found.content_id != content_id:
        raise ApiError(404, "not_found", "That version is of another song")
    return found


@router.get("/{content_id}/lyrics")
async def lyrics(
    content_id: str, request: Request, who: Operator | Node = Depends(anyone)
) -> Lyrics:
    found = services(request)
    current = found.library.manifest(found.library.get(content_id)["manifest"])
    track = current.track("lyrics")
    assert track is not None
    return Lyrics.model_validate_json(found.store.read_bytes(track.blob.sha256))


class LyricsEdit(BaseModel):
    base: str
    lyrics: Lyrics


@router.put("/{content_id}/lyrics")
async def save_lyrics(
    content_id: str, body: LyricsEdit, request: Request, who: Operator = Depends(operator)
) -> Content:
    """A new version with edited lyrics; `base` is the manifest the editor started from."""
    from karaoke_engine.package import with_lyrics

    found = services(request)
    current = found.library.get(content_id)
    if current["manifest"] != body.base:
        raise ApiError(409, "version_conflict", "The song changed meanwhile", current=current)
    _, blob = with_lyrics(found.library.manifest(body.base), body.lyrics, found.store)
    content = found.library.register(blob.sha256)
    found.events.publish("content", content=content)
    return Content.model_validate(content)


@router.delete("/{content_id}", status_code=204)
async def trash(content_id: str, request: Request, who: Operator = Depends(operator)) -> Response:
    found = services(request)
    found.library.trash(content_id)
    found.events.publish("content", content=found.library.get(content_id))
    return Response(status_code=204)


@router.post("/{content_id}/restore")
async def restore(content_id: str, request: Request, who: Operator = Depends(operator)) -> Content:
    found = services(request)
    found.library.restore(content_id)
    content = found.library.get(content_id)
    found.events.publish("content", content=content)
    return Content.model_validate(content)


class GcView(BaseModel):
    kept: int
    deleted: int
    freed_bytes: int
    purged_contents: int
    usage_bytes: int


@router.post("/gc", include_in_schema=True)
async def gc(request: Request, who: Operator = Depends(operator)) -> GcView:
    found = services(request)
    report = found.library.collect(found.settings.quota_bytes)
    return GcView(**report.__dict__, usage_bytes=found.library.usage())
