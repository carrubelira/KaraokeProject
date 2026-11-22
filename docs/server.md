# Server (v4)

`karaoke-server` is the source of truth of the distributed karaoke (plan v4, `plan-v4/00-vision.md`):
it keeps the songs in a content-addressed store, queues the work for the workers, enrols the
workers, runs the **stage** (one per backend: its queue, its session, its screens and its sound,
decision 011) and talks to the console, the screens and `kp-audio` over WebSockets. It never runs
a model: the workers do (`worker.md`).

It runs natively on Windows, Linux and macOS, on plain HTTP: everything is on one LAN.

## Starting it

`scripts/start.sh` (Linux) or `scripts\start.ps1` (Windows) prepares and starts the server,
`kp-audio` and a worker on this machine (`development.md`). By hand:

```bash
uv run karaoke-server operator add "Your name"   # prints your token for the console
uv run karaoke-server serve                       # http://0.0.0.0:8765
```

`--audio` says where the sound comes from: `auto` (the default: `kp-audio` on the `PATH` or next
to Python, started and kept running by the server), a path to `kp-audio`, `external` (a person
starts it, with `KARAOKE_AUDIO_TOKEN`) or `off` (no sound: the stage keeps time for the screens
alone). See `kp-audio.md`.

## Enrolling workers

```bash
uv run karaoke-server enroll           # a one-time token for a worker, valid 24 h
uv run karaoke-server nodes            # list; --revoke NODE_ID to cut one off
```

On the worker: `karaoke-worker enroll http://SERVER:8765 TOKEN`. Operators can also make tokens
from the console (Devices). Screens need no enrolment: any browser that opens `/pantalla` is one
(`screens.md`).

## The stage

- **One queue** with optimistic versions, and one **session**: what is on, as a versioned picture
  (`karaoke_contracts.stage.Session`) pushed to `kp-audio`, every screen and every console.
- **States**: `idle → cueing → cued → playing ⇄ paused → ended`, and `fault` when there is no
  sound to be had. A cue makes a new epoch; `kp-audio` says when it has the song ready for it.
- **Nothing plays until the operator says so**: `start` from `cued` or `paused`. If a screen that
  counts is not on the cued frame, `start` answers `409 screens_not_ready` with their ids, and the
  console asks before starting anyway (`force`); the late screen joins in step.
- **Time**: every anchor is on the server's monotonic clock (`perf_counter`). A start or a pause
  takes effect about 120 ms after it is given (more if a screen answers slowly), a seek while
  playing 400 ms after, so everything changes on the same instant.
- **The end of a song** cues the next one, which waits for the operator.
- If the master audio output goes away, the stage pauses (and so does every screen).

## Where everything lives

`%LOCALAPPDATA%\karaoke` on Windows, `~/.local/share/karaoke` elsewhere (`--data` or `KARAOKE_DATA`):

- `blobs/`: every track, video, lyrics and manifest, named by its SHA-256 (`kp-audio` reads them
  in place).
- `karaoke-v4.db`: contents, the task queue, workers, the stage's queue, its audio routing and
  each screen's settings (a v3 `karaoke.db` is left alone).
- `uploads/`: uploads that have not finished (deleted after a day).
- `logs/`.

## Upkeep

- **Trash**: a deleted song stays 30 days, then its manifests go; `karaoke-server gc` (also run
  daily) deletes the blobs nothing refers to. `KARAOKE_QUOTA_GB` caps the store: over it the
  trash is emptied first.
- **Backups**: `karaoke-server backup DEST` copies the database and only the blobs `DEST` lacks.

## The API

- Operators: `Authorization: Bearer op_…` or the session cookie (`POST /api/session`).
- Workers: the credential they got when enrolling.
- `GET /api/blobs/{sha}` (with `Range`), `PUT /api/blobs/{sha}` (the hash is checked),
  `GET /api/blobs/{sha}/local` for workers on the server's own disk.
- Resumable uploads: `POST /api/uploads`, `HEAD`/`PATCH /api/uploads/{id}` with `Upload-Offset`.
- Jobs: `POST /api/jobs` (an upload or a link, or an MP4 export; `auto_confirm` skips the review
  when the analysis is sure), `…/{cancel,pause,resume,retry}`, `POST …/confirm` (the operator's
  title, artist, language and lyrics after the analysis, and optionally `add_to_queue`),
  `GET …/tasks/{key}/log` (the whole log once the task ended, the last lines while it runs),
  `PATCH` for priority and pinning.
- Workers: `POST /api/worker/lease` (long poll), `/api/worker/heartbeat`,
  `/api/tasks/{id}/{progress,log,complete,fail}`. A report for a task that is no longer running
  (finished, cancelled, given to another worker) is refused, so a late one never brings a
  finished task back.
- The stage: `GET /api/stage`; `POST /api/stage/commands` (`cue`, `start`, `pause`, `seek`,
  `next`, `previous`, `stop`, `volume`, `pitch`; `force` to start with screens not ready);
  `GET/PUT /api/stage/queue` with optimistic versions (`409` with the current queue on a
  conflict) and `POST /api/stage/queue/items`, which adds to the end (or the front) whatever the
  queue is; `PUT /api/stage/audio` (routing and calibration).
- Screens: `PUT /api/screens/{id}/config`, `DELETE /api/screens/{id}` (one that is closed); the
  screens' own socket `/api/screens/ws` and `GET /api/screens/blobs/{sha}` (only the songs on the
  stage and in the queue; open to the LAN).
- `kp-audio`: its socket `/api/audio/ws`, on the loopback, with the secret of this start.
- The console's socket is `/api/events`: a snapshot (jobs, songs, the queue, the session, the
  audio, the screens, workers), then every change with a sequence number (`job`, `task`,
  `task-log`, `content`, `queue`, `session`, `audio`, `audio-status`, `screen`, `screen-status`,
  `screen-removed`, `node`, `node-removed`).

The design is in `plan-v4/decisiones/004-servidor.md` and `011-pantallas-web-y-audio-en-el-backend.md`.
