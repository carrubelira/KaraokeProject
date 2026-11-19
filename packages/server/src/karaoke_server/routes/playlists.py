"""Production playlists, edited by several controls at once (optimistic versions)."""

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, Field

from karaoke_contracts.control import Playlist
from karaoke_server.auth import Node, Operator, anyone, operator
from karaoke_server.errors import ApiError
from karaoke_server.routes._deps import services

router = APIRouter(prefix="/api/playlists", tags=["playlists"])


class NewPlaylist(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    player_id: str | None = None


@router.get("")
async def list_playlists(
    request: Request, who: Operator | Node = Depends(anyone)
) -> list[Playlist]:
    return services(request).playlists.all()


@router.post("", status_code=201)
async def create(
    body: NewPlaylist, request: Request, who: Operator = Depends(operator)
) -> Playlist:
    return services(request).playlists.create(body.name, body.player_id)


@router.get("/{playlist_id}")
async def get(
    playlist_id: str, request: Request, who: Operator | Node = Depends(anyone)
) -> Playlist:
    return services(request).playlists.get(playlist_id)


@router.put("/{playlist_id}")
async def save(
    playlist_id: str, body: Playlist, request: Request, who: Operator = Depends(operator)
) -> Playlist:
    if body.id != playlist_id:
        raise ApiError(422, "id_mismatch", "The body is another playlist")
    found = services(request)
    library = {c["id"] for c in found.library.contents()}
    unknown = sorted({item.content_id for item in body.items} - library)
    if unknown:
        raise ApiError(
            422, "unknown_contents", "Some songs are not in the library", contents=unknown
        )
    saved = found.playlists.save(body)
    await found.players.playlist_changed(saved)
    return saved


@router.delete("/{playlist_id}", status_code=204)
async def delete(playlist_id: str, request: Request, who: Operator = Depends(operator)) -> Response:
    services(request).playlists.delete(playlist_id)
    return Response(status_code=204)
