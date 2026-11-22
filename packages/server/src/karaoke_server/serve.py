"""Running the server: one uvicorn process, with TLS from its own certificate."""

import logging

import uvicorn

from karaoke_server.app import build_services, create_app
from karaoke_server.config import Settings
from karaoke_server.logs import setup_logging
from karaoke_server.tls import ensure_certificate, fingerprint

logger = logging.getLogger(__name__)


def serve(settings: Settings, verbose: bool = False) -> None:
    setup_logging(settings.logs_dir, verbose)
    settings.ensure_dirs()
    ssl: dict[str, str] = {}
    pin = ""
    if settings.tls:
        cert, key = ensure_certificate(settings.tls_dir, settings.tls_names)
        ssl = {"ssl_certfile": str(cert), "ssl_keyfile": str(key)}
        pin = fingerprint(cert)
    app = create_app(settings, services=build_services(settings, fingerprint=pin))
    scheme = "https" if settings.tls else "http"
    logger.info("karaoke server on %s://%s:%s", scheme, settings.host, settings.port)
    if pin:
        logger.info("certificate fingerprint %s", pin)
    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        log_config=None,
        server_header=False,
        timeout_graceful_shutdown=5,
        ws_ping_interval=15,
        **ssl,  # type: ignore[arg-type]
    )
