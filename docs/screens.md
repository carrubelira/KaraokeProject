# Screens (v4)

A screen is any browser on the LAN that opens `http://SERVER:8765/pantalla`: a laptop on
Windows, Linux or macOS, or a kiosk (decision 011). Every screen shows the same thing, in step:
the song's video and its lyrics, and between songs who sings next. The sound comes from the
backend (`kp-audio.md`), never from a screen.

```
http://SERVER:8765/pantalla                      a screen; this browser keeps its id
http://SERVER:8765/pantalla?screen=sala-hdmi-1   a screen with the id given (one per monitor)
http://SERVER:8765/pantalla?kiosk                no full-screen button (the kiosk is full screen)
http://SERVER:8765/pantalla?preview              shown on the stage, never waited for
```

Screens need no sign-in: they only show what is on. The console (Devices) lists every screen
that has opened, its state, how well it keeps time and what it downloads, and is where each one
is named and told what to show (video and lyrics, lyrics only, video only, off), with which
style of lyrics, how late its TV really is and the tallest video it should download.

## How a screen works

It is a state machine (`web/src/lib/screen/machine.ts`, a pure reducer the tests drive):

| State | When |
|---|---|
| `connecting` | no line to the server yet (or lost, with nothing on) |
| `idle` | nothing is cued |
| `provisioning` | downloading the song cued (its progress shows) |
| `syncing` | the song is here: looking for its frame at the position cued |
| `waiting` | on that frame, ready; the operator has not started yet |
| `playing` | following the timeline |
| `paused` | held on a frame |
| `error` | something it cannot get past (a video this browser cannot play); a reload |

Besides the state, it reports flags: `offline` (the line dropped mid-song: the picture goes on
with the last anchor), `hidden` (the tab is not visible: the browser stops drawing),
`degraded` (the video cannot keep up) and `fullscreen`.

- **The session**: the server pushes the stage's session (what is on and an anchor: a position
  that holds at an instant, on the server's clock, moving at a rate). A start, a pause or the end
  of a song carries on from the frame shown, so the picture only starts or stops; another song or
  a seek looks for the frame again.
- **The clock**: the screen asks the server's time every two seconds (eight at once on
  connecting). Of every ten seconds only the quickest answer counts, and a line through them gives
  the offset and the drift between the two crystals; corrections are slewed (0.5 ms per second).
- **The picture**: each frame is drawn for the instant it will be seen (the next refresh plus
  the TV's delay). A muted `<video>` plays the song's video; its speed is trimmed (±3 %) to keep it
  on the timeline, and it jumps when it is more than 150 ms off. `requestVideoFrameCallback` says
  which frame is shown and when; without it, the element's time is read every refresh.
- **Ahead**: the next songs are downloaded while one plays, and the next one waits in a second
  `<video>`, stopped on its first frame.
- **Storage**: the blobs stay in IndexedDB, checked by SHA-256 as they arrive (in a worker); a
  dropped download goes on where it stopped (`Range`).

The bench (`web/src/lib/screen/sync.test.ts`) runs the clock and the video servo against a
simulated network (jitter, Wi-Fi spikes), drifting crystals, refresh rates and slow jumps: on a
cable the frame shown always holds the audio heard; on a bad Wi-Fi, within 2 ms at p95. On a
Windows laptop, two Edge screens measured 1 ms apart from each other and about 10 ms from the
timeline (a third of a 30 fps frame).

## Kiosks

A kiosk is a full-screen browser that opens `/pantalla?kiosk&screen=<name>`: Tauri (planned for
the Raspberry Pi, decision 011), or Chromium in kiosk mode. A Raspberry Pi 5 decodes no H.264 in
hardware: give its screens a 720p limit in the console.
