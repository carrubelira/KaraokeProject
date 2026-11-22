# Worker (v4)

`karaoke-worker` runs the engine for the server on a machine with an NVIDIA GPU (Windows or Linux,
natively). It connects out to the server, so it works behind NAT and over Tailscale.

```bash
uv sync --extra ml --inexact                         # torch and the models' libraries
uv run karaoke-worker info                           # what this machine offers
uv run karaoke-worker enroll https://SERVER:8765 TOKEN --fingerprint FINGERPRINT
uv run karaoke-worker run
```

- **Tasks**: `fetch` (a link with yt-dlp; needs the internet and `uvx`), `analyze` (which song
  it is and its lyrics, below; every worker with the internet takes it), `make` (a karaoke from a
  song) and `render` (the MP4). Each runs in a child process with its memory capped: a systemd scope
  on Linux, a Job Object on Windows (it also dies with the worker).
- **GPU**: one GPU task at a time (concurrency by VRAM: 4 GB hold one model), and up to two
  downloads alongside.
- **Same machine as the server**: enrol with `--same-host`; it reads the server's blobs from disk.
- **Same machine as a player**: `--player-lock FILE` names the file the player touches while it
  plays; meanwhile the worker takes no GPU work.
- **Cache**: the blobs it fetched or made stay in its data folder, so the next task on the same
  song does not download them again (the server prefers the worker that has them).

- **What it is doing, live** (`feed.py`): every task reports its stage and the step inside it
  (`separate · voz`, `download · 40 %`), in order and at most once a second, through one sender
  per task, so a report can never arrive after the task is complete. The lines yt-dlp and the
  engine write go to the server in small batches (`POST /api/tasks/{id}/log`) for the live view,
  and the whole log goes up as a blob when the task ends, failed or not.
- **Telemetry**: GPU use, VRAM and temperature from NVML; CPU and RAM from psutil (Windows
  included), with every heartbeat.

## Which song is it? (`analyze`)

`identify.py` works out what a link or a file is before anything heavy runs, step by step:

1. What the page says (YouTube Music names the track, artist and album; a plain video only has a
   title like «Artist - Title (Official Video)», which is cleaned), or a file's tags.
2. A Chromaprint fingerprint of the first two minutes (ffmpeg's `chromaprint` muxer, or `fpcalc`),
   looked up in [AcoustID](https://acoustid.org), which answers with MusicBrainz recordings.
3. MusicBrainz: the recording's artists, first release, year and the language of its lyrics; the
   cover from the Cover Art Archive.
4. LRCLIB: the lyrics, searched with the best name found, closest in duration first.

AcoustID needs an application key (free, at
[acoustid.org/new-application](https://acoustid.org/new-application)) on each worker:
`karaoke-worker acoustid-key KEY` keeps it in the worker's settings (`KARAOKE_ACOUSTID_KEY` in its
environment wins over it). Without it the sound is not looked up and the review says so. Network failures
never fail the task: the operator reviews whatever was found.

`--fake` pretends with the synthetic demo, without a GPU (tests, trying the system).
The design is in `plan-v4/decisiones/005-worker.md`.
