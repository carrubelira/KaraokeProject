# kp-audio (v4)

`kp-audio` is the backend's audio engine (decision 011): it runs on the server's machine, follows
the stage's session and sends each stem to the sound cards and DACs connected there, every output
on the same instant. The picture and the lyrics are web screens (`screens.md`); nothing else plays
sound.

The server starts it and starts it again if it stops. It finds it on the `PATH` or next to
Python's executable (`--audio auto`, the default), or where `--audio PATH` says. `--audio off`
runs the stage without sound (development, the browser tests); `--audio external` leaves
starting it to a person, with the secret in `KARAOKE_AUDIO_TOKEN`:

```bash
KARAOKE_AUDIO_TOKEN=secret karaoke-server serve --audio external
KARAOKE_AUDIO_TOKEN=secret kp-audio run --server http://127.0.0.1:8765 --store DATA/blobs
kp-audio devices             # the audio outputs and their ids, for the routing
kp-audio run --diagnose ...  # also logs drift, offsets and levels every second
```

## What it does

- **The session**: the server pushes every version of it (the song on, its manifest, the anchor
  that says where the song is at which instant, the key, the volume). kp-audio decodes the song
  as soon as it is cued and says it is **ready** for that epoch; the server only lets the operator
  start once it is. The next song in the queue is decoded ahead, so cueing it is instant.
- **Its own disk**: it reads the blobs from the server's store (`--store`), nothing is downloaded.
- **Decoding**: the stems are Opus in Ogg; the pages are read in Rust and the packets decoded by
  libopus, dropping the pre-skip and the padding of the last packet (the same samples `ffmpeg`
  gives). No FFmpeg, neither in the build nor on the machine.
- **Time**: the timeline is the server's monotonic clock; kp-audio learns its offset from `time`
  answers (the one with the shortest round trip wins) and learns it again on every reconnection.
- **Outputs**: the routing (set in the console, Outputs) sends each stem to any outputs with a
  gain and a delay; without one, both stems go to the default output. Each output follows the
  timeline through its own resampler (a few hundred ppm at most), so two sound cards stay within a
  millisecond (`kp-syncbench`).
- **Key**: Signalsmith Stretch on the guide vocals and the music alike; its latency is
  compensated so changing the key never moves the song.
- **The end of a song**: it holds at the exit point by itself, before the server says it ended.
- **When an output goes away**: if it is the master, playback pauses and the server pauses every
  screen too; otherwise it carries on. Each output can be set otherwise. It reconnects when the
  device is back.
- **What does not work** goes into its status (`errors`: an output that could not be opened or
  went away, a song that did not load, the master lost) until it works again.
- **Calibration**: per output, in milliseconds, from the console.

## Building

Rust (stable), a C/C++ compiler (MSVC from the Build Tools on Windows) and:

- **cmake**, for libopus when the system has none (on Linux, `libopus-dev` skips it). On Windows the
  Build Tools bring one: put it on the `PATH` or point `CMAKE` at it
  (`…\BuildTools\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin\cmake.exe`).
- **libclang**, for Signalsmith Stretch's bindings (the `pitch` feature, on by default): on Windows
  the Build Tools' "C++ Clang tools for Windows" component, LLVM, or `pip install libclang`, with
  `LIBCLANG_PATH` pointing at the folder with `libclang.dll`; Xcode's on macOS; `clang` on Linux.
  Without it, `--no-default-features --features native` builds without the key change.

```bash
cd audio && cargo build --release -p kp-audio
```

## Tests

- `make audio`: the crates' tests and the sync bench (audio↔audio).
- `make e2e-v4`: the server, a worker with the fake engine and kp-audio with two virtual
  outputs, from an upload to a song that only sounds once the operator starts it, in sync on both
  outputs, transposed and paused.

The design is in `plan-v4/decisiones/001-motor-del-reproductor.md`, `002-banco-de-sincronia.md`,
`006-reproductor.md` and `011-pantallas-web-y-audio-en-el-backend.md`.
