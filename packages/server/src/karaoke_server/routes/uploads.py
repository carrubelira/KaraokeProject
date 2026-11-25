"""Resumable uploads from the control UI (see karaoke_server.uploads)."""

from fastapi import APIRouter, Depends, Header, Request, Response
from pydantic import BaseModel, Field

from karaoke_server.auth import Operator, operator
from karaoke_server.routes._deps import services

router = APIRouter(prefix="/api/uploads", tags=["uploads"])

CHUNK_LIMIT = 64 * 1024 * 1024


class NewUpload(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    size: int = Field(gt=0)


class UploadView(BaseModel):
    id: str
    filename: str
    size: int
    offset: int
    blob: str | None


@router.post("", status_code=201)
async def create(
    body: NewUpload, request: Request, who: Operator = Depends(operator)
) -> UploadView:
    return UploadView.model_validate(services(request).uploads.create(body.filename, body.size))


@router.get("/{upload_id}")
async def get(upload_id: str, request: Request, who: Operator = Depends(operator)) -> UploadView:
    return UploadView.model_validate(services(request).uploads.get(upload_id))


@router.head("/{upload_id}")
async def offset(upload_id: str, request: Request, who: Operator = Depends(operator)) -> Response:
    upload = services(request).uploads.get(upload_id)
    return Response(
        headers={"Upload-Offset": str(upload["offset"]), "Upload-Length": str(upload["size"])}
    )


@router.patch("/{upload_id}")
async def append(
    upload_id: str,
    request: Request,
    upload_offset: int = Header(alias="Upload-Offset", ge=0),
    who: Operator = Depends(operator),
) -> UploadView:
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > CHUNK_LIMIT:
            from karaoke_server.errors import ApiError

            raise ApiError(413, "chunk_too_big", "Send at most 64 MiB per request")
    return UploadView.model_validate(
        services(request).uploads.append(upload_id, upload_offset, bytes(body))
    )
