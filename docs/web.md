# The console (v4)

The web app is the **console** of the distributed karaoke (plan v4 §7): an operator adds songs,
reviews what the system found, follows the work on every worker, fills each screen's queue and
drives what is on air. It talks to the v4 server only (`docs/server.md`); the songs play on the
native player (`docs/player.md`), not in the browser. The design decisions are in
[`plan-v4/decisiones/010-consola.md`](plan-v4/decisiones/010-consola.md) (in Spanish).

## Running it

```bash
uv run karaoke-server operator add "Your name"     # your token
uv run karaoke-server serve --no-tls --port 8765   # development: plain HTTP
pnpm --dir web dev                                 # http://localhost:5173, proxied to :8765
```

`KARAOKE_SERVER` points the dev server elsewhere (an `https://` server works: the proxy does not
check its self-signed certificate). In production `make serve` serves the built app from the
server itself, over its TLS.

## What it looks like

A broadcast control room at night, over a live 3D signal field:

- **The strip** (top): the screen the console drives (one button per screen, each with its tally
  lamp), the big ON AIR / STANDBY tally, the server's clock, and the health of the system in one
  line (workers online, jobs running, songs to review, alerts). Every count opens its section.
- **The rail** (left; at the bottom on a phone): the sections, with live counts when something
  there wants the operator.
- **The deck** (bottom, everywhere): what is on air, its position (click to jump), the transport,
  and the key and the volume on two rotary encoders (drag, scroll or arrow keys; double click
  resets).
- **The field** (behind, Three.js): a sheet of points that breathes with the work in flight; each
  worker is a core on the left whose spin and size follow its GPU and VRAM, red when a task of
  it failed, streaming particles to the hub while it works; each screen is a core on the right,
  red and pulsing on air, green when cued, amber when something on it is broken. It rests when
  the tab is hidden; Settings → Effects (full, calm, off) and the system's reduced motion calm
  it. It is decoration: every state it shows is also written in the interface.

The tally colours mean the same everywhere: red on air, green cued or healthy, amber waiting for
someone or warning, cyan information in motion, grey idle. Martian Mono is for data, Figtree for
prose, Unbounded for the few big names (`src/lib/ui/styles/console.css`).

## Sections

| Path | What |
|---|---|
| `/` Live | The program monitor of the chosen screen (its lyrics filling in sync, as a confidence monitor), its alerts, and its queue: search and Enter adds a song, rows drag to reorder, the singer is typed in place. |
| `/engadir` Add | One field: paste a link (or drop a file anywhere). The analysis runs at once and shows its steps live (download, metadata, fingerprint, AcoustID, MusicBrainz, lyrics); then the review: the best guess filled in, the other guesses with their source and certainty, the lyrics found (timed ones first), searched again, pasted or left out to transcribe. "Process" (or "Process and queue on SCREEN") starts the karaoke. |
| `/traballos` Jobs | Every job as a pipeline of its tasks: state, what the worker is doing (stage and step), progress, time left, attempts; a failure says why and what to do (retry, retry on another worker); each task's log opens below, live while it runs. |
| `/biblioteca` Library | Every song, fuzzy search, to the queue in one key. |
| `/nodos` Nodes | Workers and screens as rack units: GPU, VRAM, CPU, RAM and temperature live, what each runs, each screen's outputs and problems; enrolment with the exact command to paste. |
| `/saidas` Outputs | The routing matrix of the chosen screen (a patch bay), the master output, calibration, what each display shows. |
| `/editar/[id]` | The lyrics editor. |
| `/axustes` Settings | Language (Galician, English), effects, server, song identification, shortcuts. |

## Keyboard first

Every action is a command in one registry (`src/lib/commands/registry.svelte.ts`); the palette,
the shortcuts, the cheat sheet and the settings page all come from it.

| Keys | What |
|---|---|
| `Ctrl/⌘ K` | command palette: every command, song and node, fuzzy search |
| `?` | every shortcut that works here |
| `g` then `d n t b w s a` | Live, Add, Jobs, Library, Nodes, Outputs, Settings |
| `Ctrl/⌘ N` | Add |
| `Space` · `n` / `p` · `←` / `→` | play or pause · next / previous · ±5 s |
| `+` / `-` · `[` / `]` · `Ctrl/⌘ 0` | volume · key · original key |
| `s` | the next screen |
| `Ctrl/⌘ Z` · `Ctrl/⌘ Shift Z` | undo · redo (queue edits, trash) |
| `/` | search on the page |

In Live `j`/`k` move, `Enter` cues the song, `Shift+Enter` plays it now, `Delete` removes it,
`Alt+↑/↓` reorders; in the Library `a` adds to the screen's queue (`Shift+A` right after the song
on air), `e` opens the editor, `m` exports an MP4, `Delete` sends to the trash; in Jobs `Shift+R`
retries every failed job; in Outputs `Ctrl/⌘ S` saves.

## Live and never stale

- Everything comes through one WebSocket (`/api/events`): a snapshot, then every change, each
  with a sequence number. A gap in the numbers, or a server that stops answering pings, drops the
  line and opens it again, which brings a fresh snapshot: nothing shown can stay stale.
- Changes show at once and are confirmed afterwards; if the server says no they are reverted with
  a notice. A queue edit that meets a newer version is applied again on top of it.

## Pieces

- `src/lib/control/`: the API client, the live store (`state.ts` is pure: one function applies
  each event), resumable uploads, notices.
- `src/lib/console/`: the strip, the rail, the deck, the encoder, the program monitor, the
  analysis and review cards, the job pipeline, the log view, the icons, and `scene/` (the 3D
  field and the numbers it is fed).
- `src/lib/commands/`: shortcuts, the registry, fuzzy search, undo.
- `src/lib/shell/`: the operator's actions and preferences, intake (a link pasted or a file
  dropped anywhere), the palette, the cheat sheet, sign-in, keyboard selection in lists.

## Tests

```bash
pnpm --dir web lint && pnpm --dir web check && pnpm --dir web test
pnpm --dir web test:e2e   # needs Playwright's Chromium (or PLAYWRIGHT_CHROMIUM=/path)
```

The `control` project starts a v4 server with a fake worker and a screen
(`e2e/control/serve.py`) and drives the console: sign in, add a song and review it, follow it in
Jobs, queue it twice, remove and undo, the singer, the palette, the cheat sheet, response times
and axe's WCAG 2 AA rules on every section. The `lyrics` project compares screenshots of the
lyrics component.
