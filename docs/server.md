# Server (v4)

`karaoke-server` is the source of truth of the distributed karaoke (plan v4, `plan-v4/00-vision.md`):
it keeps the songs in a content-addressed store, queues the work for the workers, enrols the
workers and players, and talks to the control UI and the players over WebSockets. It never runs
a model: the workers do (`worker.md`).

It runs natively on Windows, Linux and macOS; WSL is no longer needed.

## Starting it

```bash
uv run karaoke-server operator add "Your name"   # prints your token for the control UI
uv run karaoke-server serve                       # https://0.0.0.0:8765
```

The first start makes a self-signed certificate (`tls/server.crt`). Nodes pin it when they enrol:

```bash
uv run karaoke-server fingerprint
```

Add the names it is reached at with `--name` (a Tailscale name, a fixed LAN address); the machine's
own names are always in. `--no-tls` serves plain HTTP for development only.

## Enrolling workers and players

```bash
uv run karaoke-server enroll worker    # a one-time token, valid 24 h
uv run karaoke-server enroll player
uv run karaoke-server nodes            # list; --revoke NODE_ID to cut one off
```

On the worker: `karaoke-worker enroll https://SERVER:8765 TOKEN --fingerprint FINGERPRINT`.
Operators can also make tokens from the control UI (Workers → Enrol).

## Where everything lives

`%LOCALAPPDATA%\karaoke` on Windows, `~/.local/share/karaoke` elsewhere (`--data` or `KARAOKE_DATA`):

- `blobs/`: every track, video, lyrics and manifest, named by its SHA-256.
- `karaoke-v4.db`: contents, the task queue, nodes, their queues (a v3 `karaoke.db` is left
  alone).
- `uploads/`: uploads that have not finished (deleted after a day).
- `tls/`: the certificate and its key.
- `logs/`.

## Upkeep

- **Trash**: a deleted song stays 30 days, then its manifests go; `karaoke-server gc` (also run
  daily) deletes the blobs nothing refers to. `KARAOKE_QUOTA_GB` caps the store: over it the
  trash is emptied first.
- **Backups**: `karaoke-server backup DEST` copies the database and only the blobs `DEST` lacks.

## The API

- Operators: `Authorization: Bearer op_…` or the session cookie (`POST /api/session`).
- Nodes: the credential they got when enrolling.
- `GET /api/blobs/{sha}` (with `Range`), `PUT /api/blobs/{sha}` (the hash is checked),
  `GET /api/blobs/{sha}/local` for nodes on the server's own disk.
- Resumable uploads: `POST /api/uploads`, `HEAD`/`PATCH /api/uploads/{id}` with `Upload-Offset`.
- Jobs: `POST /api/jobs` (an upload or a link, or an MP4 export; `auto_confirm` skips the review
  when the analysis is sure), `…/{cancel,pause,resume,retry}`, `POST …/confirm` (the operator's
  title, artist, language and lyrics after the analysis, and optionally `queue_on`, a player
  whose queue gets the song once it is made), `GET …/tasks/{key}/log` (the whole log once the
  task ended, the last lines while it runs), `PATCH` for priority and pinning.
- Workers: `POST /api/worker/lease` (long poll), `/api/worker/heartbeat`,
  `/api/tasks/{id}/{progress,log,complete,fail}`. A report for a task that is no longer running
  (finished, cancelled, given to another worker) is refused, so a late one never brings a
  finished task back.
- One queue per player (made when it is enrolled; a v3/v4 playlist a player pointed at became
  its queue): `GET/PUT /api/players/{id}/queue` with optimistic versions (`409` with the current
  queue on a conflict) and `POST /api/players/{id}/queue/items`, which adds to the end (or the
  front) of whatever the queue is, with no version to match.
- Players: `PUT /api/players/{id}/config`, `POST /api/players/{id}/commands`, and their socket
  `/api/players/ws`. The control's socket is `/api/events`: a snapshot (jobs, songs, queues,
  players, nodes), then every change with a sequence number (`job`, `task`, `task-log`,
  `content`, `queue`, `player`, `player-status`, `player-command`, `node`, `node-removed`).

The design is in `plan-v4/decisiones/004-servidor.md`.
