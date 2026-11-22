# Player (v4)

`kp-player` is the native karaoke player (plan v4 §6): it follows the server's orders and plays
every output of the machine in sync. It ships for **Windows** (NVIDIA or any GPU) and **macOS**;
Linux builds are for development.

```bash
kp-player enroll https://SERVER:8765 TOKEN --fingerprint FINGERPRINT --name sala
kp-player devices        # audio outputs and their ids, for the routing
kp-player run            # a window on every screen, sound on the routed outputs
kp-player run --diagnose # also logs drift, offsets and levels every second
```

`karaoke-server enroll player` gives the token, `karaoke-server fingerprint` the fingerprint.

## What it does

- **Its queue**: the server sends the screen's queue (`queue` messages) whenever it changes.
- **Downloads ahead**: the song on first, then the next three. It plays only what is on disk and
  checked by hash; downloads resume. With `--same-host` (on the server's machine) it reads the
  server's files directly.
- **Outputs**: the routing (set from the control UI) sends each stem to any outputs with a gain
  and a delay; without one, both stems go to the default output. Each output follows the timeline
  through its own resampler (a few hundred ppm at most), so two sound cards stay within a
  millisecond. A screen shows what the master output is actually playing.
- **Screens**: a borderless full-screen window per monitor (video and lyrics, lyrics only, or
  video only, per screen). Each frame is drawn for the instant it will be shown.
- **Pitch**: Signalsmith Stretch on the guide vocals and the music alike; its latency is
  compensated so changing the key never moves the song.
- **When an output goes away** (the TV is switched off): if it is the master, playback pauses;
  otherwise it carries on. Each output can be set otherwise. It reconnects when the device is back.
- **Device ids** are the system's name for the output; two outputs with the same name (two
  monitors of one model on the same graphics card) get `#2`, `#3`… in the order the system lists
  them.
- **What does not work** goes into its status (`errors`: an output that could not be opened or
  went away, a song that did not load, the master lost) until it works again, so the console
  shows it next to the screen.
- **Without the server** it plays on what it has, and catches up when the server is back.
- **Calibration**: per output and per screen (milliseconds), from the control UI, saved by
  device id.
- **A worker on the same machine**: while it plays, the player touches `DATA/playing`; enrol the
  worker with `--player-lock DATA/playing` and it will not start GPU work meanwhile.

## Building

Rust (stable) and FFmpeg 7 development files. On Windows, set `FFMPEG_DIR` to an unpacked
"shared" FFmpeg build and put its `bin` on `PATH`; `bindgen` also needs `libclang` (LLVM, or
point `LIBCLANG_PATH` at a folder with `libclang.dll`). On macOS, use `brew install ffmpeg@7 pkg-config`.
Then:

```bash
cd player && cargo build --release -p kp-player
```

Put the themes folder (`packages/engine/src/karaoke_engine/subtitles/themes`) next to the binary
as `themes/`, or point `KARAOKE_THEMES` at it.

## Tests

- `make player`: the crates' tests, including the layout against the shared cases and the sync
  bench.
- `make e2e-v4`: server, a worker with the fake engine, and the player headless with two
  simulated outputs, from an upload to synchronised playback, transposition and pause.

The design is in `plan-v4/decisiones/001-motor-del-reproductor.md`, `002-banco-de-sincronia.md`
and `006-reproductor.md`.
