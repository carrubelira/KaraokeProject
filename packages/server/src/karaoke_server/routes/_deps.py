"""Shortcuts route modules share."""

from fastapi import Request, WebSocket

from karaoke_server.services import Services


def services(request: Request) -> Services:
    found: Services = request.app.state.services
    return found


def ws_services(websocket: WebSocket) -> Services:
    found: Services = websocket.app.state.services
    return found
