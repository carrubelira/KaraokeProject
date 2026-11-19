"""`karaoke-worker`: enrol with a server once, then run and take tasks."""

import argparse
import asyncio
import logging
import sys
from collections.abc import Sequence
from importlib import metadata
from pathlib import Path

from karaoke_contracts.cas import BlobStore
from karaoke_contracts.nodes import Enrollment
from karaoke_worker import system
from karaoke_worker.config import WorkerConfig, default_data_dir

CERT = "server.crt"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="karaoke-worker", description="Karaoke worker (v4).")
    parser.add_argument(
        "--version",
        action="version",
        version=f"karaoke-worker {metadata.version('karaoke-worker')}",
    )
    parser.add_argument("--data", type=Path, default=None, help="data folder")
    commands = parser.add_subparsers(dest="command", required=True)
    enrol = commands.add_parser("enroll", help="enrol with a server using a one-time token")
    enrol.add_argument("server", help="e.g. https://192.168.1.20:8765")
    enrol.add_argument("token")
    enrol.add_argument("--name", default=None, help="how the control shows it")
    enrol.add_argument("--fingerprint", help="the server's (karaoke-server fingerprint)")
    enrol.add_argument("--no-internet", action="store_true", help="do not take downloads")
    enrol.add_argument("--same-host", action="store_true", help="it runs on the server's machine")
    enrol.add_argument("--player-lock", help="file a player on this machine touches while playing")
    run = commands.add_parser("run", help="take and run tasks until stopped")
    run.add_argument("--fake", action="store_true", help="pretend (tests, trying the system)")
    run.add_argument("-v", "--verbose", action="store_true")
    commands.add_parser("info", help="print what this machine offers")
    args = parser.parse_args(argv)
    data = args.data or default_data_dir()
    if args.command == "info":
        print(system.capabilities(["fetch", "make", "render"], True).model_dump_json(indent=2))
        return 0
    if args.command == "enroll":
        return _enrol(args, data)
    return _run(args, data)


def _enrol(args: argparse.Namespace, data: Path) -> int:
    import socket

    from karaoke_worker.client import enrol

    name = args.name or socket.gethostname()
    caps = system.capabilities(["fetch", "make", "render"], not args.no_internet, args.same_host)
    request = Enrollment(token=args.token, kind="worker", name=name, capabilities=caps)
    try:
        enrolled = enrol(args.server, args.token, request, data / CERT, args.fingerprint)
    except Exception as exc:  # noqa: BLE001 - shown to the person typing the command
        print(f"error: {exc}", file=sys.stderr)
        return 1
    config = WorkerConfig(
        server=args.server.rstrip("/"),
        node_id=enrolled.node_id,
        credential=enrolled.credential,
        fingerprint=enrolled.server_fingerprint,
        name=name,
        internet=not args.no_internet,
        player_lock=args.player_lock,
    )
    print(f"enrolled as {enrolled.node_id}; settings in {config.save(data)}")
    return 0


def _run(args: argparse.Namespace, data: Path) -> int:
    from karaoke_worker.agent import Agent
    from karaoke_worker.child import ProcessSpawner, SpawnSettings
    from karaoke_worker.client import ServerClient
    from karaoke_worker.download import YtDlp
    from karaoke_worker.tasks import Context

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    config = WorkerConfig.load(data)
    client = ServerClient(config.server, config.credential, data / CERT)
    ctx = Context(
        client=client,
        store=BlobStore(data / "blobs"),
        work=data / "work",
        spawner=ProcessSpawner(SpawnSettings(data_dir=data)),
        downloader=YtDlp(YTDLP),
        fake=args.fake or config.fake_engine,
    )
    agent = Agent(ctx, player_lock=Path(config.player_lock) if config.player_lock else None)
    try:
        asyncio.run(agent.run_forever())
    except KeyboardInterrupt:
        pass
    finally:
        client.close()
    return 0


# yt-dlp changes every week to keep up with the sites, so it runs at its latest release, apart
# from the worker's own environment. Node is the JavaScript runtime YouTube now requires.
YTDLP = ("uvx", "--from", "yt-dlp[default]@latest", "yt-dlp", "--js-runtimes", "node")
