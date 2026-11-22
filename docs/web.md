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

A plain desktop application in a sober dark grey, the same in every section:

- **The sidebar** (left; one row of sections on top on a phone): the sections in words, a count
  on Processing when something there wants the operator (red for failures, amber for reviews),
  and at its foot whether the server answers and who is signed in. Galicia's coastline is drawn
  faintly behind it (Natural Earth, public domain): the one ornament, kept in the background.
- **The page**: a header (title, one line saying what the page is for, its main action), then
  panels with tables. Every list is a table with column headings; every state is a badge with its
  name in words.
- **The player bar** (bottom, everywhere): the screen being driven (a select), its state, what it
  plays and where (click the line to jump), previous / play or pause / next / stop, the key
  (− 0 +) and the volume.

One family, IBM Plex Sans, and IBM Plex Mono for times and codes (`scripts/build_web_fonts.py`
subsets them; SIL OFL). One accent, a blue, for what can be clicked and what is selected. Status
colours only where a state is shown: green working or done, amber waiting for someone or a
warning, red an error. The pieces (page header, panel, table, badge, button, field, tabs, empty
state, notice) are in `src/lib/ui/styles/app.css`; pages add only their layout.

## Sections

| Path | What |
|---|---|
| `/` Playback | What the chosen screen plays (a preview of its lyrics in sync, the singer, the key, what comes next, its alerts) and its queue as a table: search above it and Enter adds a song, rows drag to reorder, the singer is typed in place. |
| `/biblioteca` Library | Every song in a table (title, artist, language, length, version), searched, to the queue in one key. |
| `/engadir` Add song | Paste a link (or upload or drop a file). The analysis runs at once and shows its steps (download, page details, fingerprint, AcoustID, MusicBrainz, lyrics); then the review: the best guess filled in, the other matches with their source and certainty, the lyrics found (timed ones first), searched again, pasted or left out to transcribe. "Make the karaoke" (or "Make it and queue it on SCREEN") starts the work. |
| `/procesamento` Processing | One row per song being made: status, the step it is on with its progress, the computer doing it, the time. A row opens to show every step (download, analysis, making the karaoke, or the video) with its own status, computer, attempts and time, why one failed and what to do (retry, retry on another computer), and each step's log, live while it runs. Tabs filter by in progress, to review, failed, finished. |
| `/equipos` Devices | Two tables: processing computers (status, GPU, GPU memory, CPU, memory, temperature, current work) and screens (status, song, monitors and sound outputs, alerts); adding one shows the exact command to paste. |
| `/saidas` Outputs | For the chosen screen: which sound output gets the music and the guide vocals (gain, delay), the main output, calibration, what happens if one disconnects, and what each monitor shows. |
| `/editar/[id]` | The lyrics editor. |
| `/axustes` Settings | Language (Galician, English), server, song identification, session, shortcuts. |

## Keyboard first

Every action is a command in one registry (`src/lib/commands/registry.svelte.ts`); the palette,
the shortcuts, the cheat sheet and the settings page all come from it.

| Keys | What |
|---|---|
| `Ctrl/⌘ K` | command palette: every command, song and node, fuzzy search |
| `?` | every shortcut that works here |
| `g` then `r b n p e s a` | Playback, Library, Add song, Processing, Devices, Outputs, Settings |
| `Ctrl/⌘ N` | Add song |
| `Space` · `n` / `p` · `←` / `→` | play or pause · next / previous · ±5 s |
| `+` / `-` · `[` / `]` · `Ctrl/⌘ 0` | volume · key · original key |
| `s` | the next screen |
| `Ctrl/⌘ Z` · `Ctrl/⌘ Shift Z` | undo · redo (queue edits, trash) |
| `/` | search on the page |

In Playback `j`/`k` move, `Enter` cues the song, `Shift+Enter` plays it now, `Delete` removes it,
`Alt+↑/↓` reorders; in the Library `a` adds to the screen's queue (`Shift+A` right after the song
on air), `e` opens the editor, `m` exports an MP4, `Delete` sends to the trash; in Processing `Shift+R`
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
- `src/lib/console/`: the sidebar, the player bar, the lyrics preview, the analysis and review
  cards, the error note, the log view, the icons.
- `src/lib/ui/`: the fonts, `app.css` (the tokens and shared pieces), the coastline.
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
Processing, queue it twice, remove and undo, the singer, the palette, the cheat sheet, response times
and axe's WCAG 2 AA rules on every section. The `lyrics` project compares screenshots of the
lyrics component.
