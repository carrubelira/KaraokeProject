"""Operators sign in with their token; the browser keeps it in an HttpOnly cookie."""

from typing import Any

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel

from karaoke_server.auth import COOKIE, Operator, operator
from karaoke_server.errors import ApiError
from karaoke_server.routes._deps import services

router = APIRouter(prefix="/api/session", tags=["session"])


class SignIn(BaseModel):
    token: str


class SessionView(BaseModel):
    id: str
    name: str
    preferences: dict[str, Any]


@router.post("")
async def sign_in(body: SignIn, request: Request, response: Response) -> SessionView:
    auth = services(request).auth
    found = auth.operator(body.token)
    if found is None:
        raise ApiError(401, "unauthorized", "That token is not an operator's")
    response.set_cookie(
        COOKIE,
        body.token,
        httponly=True,
        samesite="strict",
        secure=services(request).settings.tls,
        max_age=180 * 86400,
    )
    return SessionView(id=found.id, name=found.name, preferences=auth.preferences(found))


@router.get("")
async def current(request: Request, who: Operator = Depends(operator)) -> SessionView:
    return SessionView(
        id=who.id, name=who.name, preferences=services(request).auth.preferences(who)
    )


@router.put("/preferences")
async def save_preferences(
    preferences: dict[str, Any], request: Request, who: Operator = Depends(operator)
) -> dict[str, Any]:
    """Shortcuts, panel layouts and the rest of what an operator sets in the control UI."""
    services(request).auth.set_preferences(who, preferences)
    return preferences


@router.delete("", status_code=204)
async def sign_out(response: Response) -> Response:
    response.delete_cookie(COOKIE)
    response.status_code = 204
    return response
