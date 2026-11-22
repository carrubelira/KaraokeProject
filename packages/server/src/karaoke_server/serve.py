"""Running the server: one uvicorn process on plain HTTP (decision 011: one LAN, no TLS)."""

import logging

import uvicorn

from karaoke_server.app import build_services, create_app
from karaoke_server.config import Settings
from karaoke_server.logs import setup_logging

logger = logging.getLogger(__name__)


def serve(settings: Settings, verbose: bool = False) -> None:
    setup_logging(settings.logs_dir, verbose)
    settings.ensure_dirs()
    app = create_app(settings, services=build_services(settings))
    logger.info("karaoke server on http://%s:%s", settings.host, settings.port)
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        log_config=None,
        server_header=False,
        timeout_graceful_shutdown=5,
        ws_ping_interval=15,
    )
