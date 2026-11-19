# Worker (v4)

`karaoke-worker` runs the engine for the server on a machine with an NVIDIA GPU (Windows or Linux,
natively). It connects out to the server, so it works behind NAT and over Tailscale.

```bash
uv sync --extra ml                                   # torch and the models' libraries
uv run karaoke-worker info                           # what this machine offers
uv run karaoke-worker enroll https://SERVER:8765 TOKEN --fingerprint FINGERPRINT
uv run karaoke-worker run
```

- **Tasks**: `fetch` (a link with yt-dlp; needs the internet and `uvx`), `make` (a karaoke from a
  song) and `render` (the MP4). Each runs in a child process with its memory capped: a systemd scope
  on Linux, a Job Object on Windows (it also dies with the worker).
- **GPU**: one GPU task at a time (concurrency by VRAM: 4 GB hold one model), and up to two
  downloads alongside.
- **Same machine as the server**: enrol with `--same-host`; it reads the server's blobs from disk.
- **Same machine as a player**: `--player-lock FILE` names the file the player touches while it
  plays; meanwhile the worker takes no GPU work.
- **Cache**: the blobs it fetched or made stay in its data folder, so the next task on the same
  song does not download them again (the server prefers the worker that has them).

`--fake` pretends with the synthetic demo, without a GPU (tests, trying the system).
The design is in `plan-v4/decisiones/005-worker.md`.
