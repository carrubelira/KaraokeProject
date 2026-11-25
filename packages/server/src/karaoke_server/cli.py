"""`karaoke-server`: run the server, add operators, enrol workers, collect garbage, back up."""

import argparse
import json
import sys
from collections.abc import Sequence
from importlib import metadata
from pathlib import Path

from karaoke_server.config import Settings


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="karaoke-server", description="Karaoke server (v4).")
    parser.add_argument(
        "--version",
        action="version",
        version=f"karaoke-server {metadata.version('karaoke-server')}",
    )
    parser.add_argument("--data", type=Path, help="data folder (default: per user)")
    commands = parser.add_subparsers(dest="command", required=True)

    serve = commands.add_parser("serve", help="run the server")
    serve.add_argument("--host")
    serve.add_argument("--port", type=int)
    serve.add_argument(
        "--audio", help="kp-audio: auto (default), a path, external (started by hand) or off"
    )
    serve.add_argument("--web", type=Path, help="built control UI (default: web/build)")
    serve.add_argument("-v", "--verbose", action="store_true")

    operator = commands.add_parser("operator", help="manage operators of the control UI")
    operator_commands = operator.add_subparsers(dest="action", required=True)
    add = operator_commands.add_parser("add", help="add an operator and print their token")
    add.add_argument("name")
    operator_commands.add_parser("list", help="list operators")

    enrol = commands.add_parser("enroll", help="print a one-time token to enrol a worker")
    enrol.add_argument("kind", choices=["worker"], nargs="?", default="worker")

    nodes = commands.add_parser("nodes", help="list or revoke enrolled workers")
    nodes.add_argument("--revoke", metavar="NODE_ID")

    commands.add_parser("gc", help="delete blobs nothing refers to and the expired trash")
    copy = commands.add_parser("backup", help="copy the database and the blobs elsewhere")
    copy.add_argument("dest", type=Path)
    openapi = commands.add_parser("openapi", help="print (or write) the API's OpenAPI document")
    openapi.add_argument("--out", type=Path)

    args = parser.parse_args(argv)
    settings = Settings.from_env(data_dir=args.data)
    if args.command == "serve":
        from karaoke_server.serve import serve as run

        settings = Settings.from_env(
            data_dir=args.data,
            host=args.host,
            port=args.port,
            audio=args.audio,
            web_dir=args.web,
        )
        run(settings, args.verbose)
        return 0
    if args.command == "openapi":
        import tempfile

        from karaoke_server.app import create_app

        # The document only needs the routes: an empty data folder, never the real one (whose
        # database the app would open and migrate).
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as scratch:
            app = create_app(Settings.from_env(data_dir=Path(scratch), audio="off"))
            text = json.dumps(app.openapi(), ensure_ascii=False, indent=2) + "\n"
        if args.out:
            args.out.write_text(text, encoding="utf-8", newline="\n")
        else:
            print(text, end="")
        return 0
    from karaoke_server.app import build_services

    found = build_services(settings)
    if args.command == "operator":
        if args.action == "add":
            print(found.auth.add_operator(args.name))
        else:
            for person in found.auth.operators():
                print(f"{person['id']}  {person['name']}  {person['created_at']}")
        return 0
    if args.command == "enroll":
        token = found.auth.new_enrollment(args.kind)
        print(token)
        print(f"valid {settings.enrollment_hours:g} h, once", file=sys.stderr)
        return 0
    if args.command == "nodes":
        if args.revoke:
            if not found.auth.revoke(args.revoke):
                print("no such node", file=sys.stderr)
                return 1
            return 0
        for row in found.db.query("SELECT id, kind, name, revoked FROM nodes ORDER BY kind"):
            state = "revoked" if row["revoked"] else "active"
            print(f"{row['id']}  {row['kind']:<6}  {row['name']}  {state}")
        return 0
    if args.command == "gc":
        report = found.library.collect(settings.quota_bytes)
        print(f"kept {report.kept}, deleted {report.deleted} ({report.freed_bytes} bytes)")
        return 0
    if args.command == "backup":
        from karaoke_server.backup import backup

        copied = backup(found, args.dest)
        print(f"{args.dest}: database and {copied} new blobs")
        return 0
    return 1
