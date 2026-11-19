"""Jobs: make a karaoke from an upload or a link, export an MP4; follow, cancel, reorder."""

from typing import Any, Literal

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field, model_validator

from karaoke_server.auth import Operator, operator
from karaoke_server.errors import ApiError
from karaoke_server.queue import BATCH, INTERACTIVE
from karaoke_server.routes._deps import services

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


class NewJob(BaseModel):
    kind: Literal["create", "render"] = "create"
    # create
    upload: str | None = Field(default=None, description="An upload id that has finished.")
    url: str | None = None
    lyrics: str | None = Field(default=None, max_length=50_000)
    lrclib: bool = False
    language: str = Field(default="gl", pattern=r"^[a-z]{2,3}$")
    title: str | None = Field(default=None, max_length=200)
    artist: str | None = Field(default=None, max_length=200)
    content_id: str | None = Field(default=None, pattern=r"^[a-z0-9][a-z0-9-]{0,79}$")
    # render
    theme: str = "clasico"
    aspect: Literal["16:9", "9:16"] = "16:9"
    vocals: float = Field(default=0.0, ge=0, le=1)
    batch: bool = Field(default=False, description="Lower priority than interactive work.")

    @model_validator(mode="after")
    def _one_source(self) -> "NewJob":
        if self.kind == "create" and (self.upload is None) == (self.url is None):
            raise ValueError("give either an upload or a url")
        if self.kind == "render" and self.content_id is None:
            raise ValueError("an export needs content_id")
        if self.url is not None and not self.url.startswith(("https://", "http://")):
            raise ValueError("the link must be http(s)")
        return self


@router.post("", status_code=201)
async def create(
    body: NewJob, request: Request, who: Operator = Depends(operator)
) -> dict[str, Any]:
    found = services(request)
    priority = BATCH if body.batch else INTERACTIVE
    if body.kind == "render":
        assert body.content_id is not None
        content = found.library.get(body.content_id)
        export = {"manifest": content["manifest"], "content_id": body.content_id,
                  "theme": body.theme, "aspect": body.aspect, "vocals": body.vocals}  # fmt: skip
        return found.queue.create_job(
            "render", f"MP4 · {content['title']}", export, priority=priority
        )
    params: dict[str, Any] = {
        "language": body.language,
        "lyrics": body.lyrics,
        "lrclib": body.lrclib,
        "title": body.title,
        "artist": body.artist,
        "content_id": body.content_id,
    }
    if body.upload is not None:
        upload = found.uploads.get(body.upload)
        if upload["blob"] is None:
            raise ApiError(409, "upload_unfinished", "The upload has not finished")
        params["source"] = upload["blob"]
        params["filename"] = upload["filename"]
        title = body.title or str(upload["filename"]).rsplit(".", 1)[0]
    else:
        params["url"] = body.url
        title = body.title or str(body.url)
    return found.queue.create_job("create", title, params, priority=priority)


@router.get("")
async def list_jobs(
    request: Request, active: bool = False, who: Operator = Depends(operator)
) -> list[dict[str, Any]]:
    return services(request).queue.jobs(active_only=active)


@router.get("/{job_id}")
async def get_job(
    job_id: str, request: Request, who: Operator = Depends(operator)
) -> dict[str, Any]:
    return services(request).queue.job(job_id)


@router.post("/{job_id}/{action}")
async def act(
    job_id: str,
    action: Literal["cancel", "pause", "resume", "retry"],
    request: Request,
    who: Operator = Depends(operator),
) -> dict[str, Any]:
    queue = services(request).queue
    return {"cancel": queue.cancel, "pause": queue.pause, "resume": queue.resume,
            "retry": queue.retry}[action](job_id)  # fmt: skip


class JobChange(BaseModel):
    priority: int | None = Field(default=None, ge=-100, le=100)
    pinned_node: str | None = None
    unpin: bool = False


@router.patch("/{job_id}")
async def change(
    job_id: str, body: JobChange, request: Request, who: Operator = Depends(operator)
) -> dict[str, Any]:
    queue = services(request).queue
    job = queue.job(job_id)
    if body.priority is not None:
        job = queue.set_priority(job_id, body.priority)
    if body.pinned_node is not None or body.unpin:
        job = queue.pin(job_id, None if body.unpin else body.pinned_node)
    return job
