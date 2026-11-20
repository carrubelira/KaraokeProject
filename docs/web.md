# Control UI (v4)

The web app is the **control** of the distributed karaoke (plan v4 §7): an operator at a keyboard
makes karaokes, follows the queue and the workers, prepares the playlists, drives the native
player and routes its outputs. It talks to the v4 server only (`docs/server.md`); the songs play
on the native player (`docs/player.md`), not in the browser.

## Running it

```bash
uv run karaoke-server operator add "Your name"     # your token
uv run karaoke-server serve --no-tls --port 8765   # development: plain HTTP
pnpm --dir web dev                                 # http://localhost:5173, proxied to :8765
```

`KARAOKE_SERVER` points the dev server elsewhere. In production `make serve` serves the built app
from the server itself, over its TLS.

## Keyboard first

Every action is a command in one registry (`src/lib/commands/registry.svelte.ts`); the palette,
the shortcuts, the cheat sheet and the settings page all come from it.

| Keys | What |
|---|---|
| `Ctrl/⌘ K` | command palette: every command, song, playlist and node, fuzzy search |
| `?` | every shortcut that works here |
| `g` then `h d b c w s n a` | Home, Live, Library, Queue, Workers, Outputs, Create, Settings |
| `Space` · `n` / `p` · `←` / `→` | play or pause · next / previous · ±5 s |
| `+` / `-` · `[` / `]` · `Ctrl/⌘ 0` | volume · key · original key |
| `j` / `k`, `↑` / `↓` · `Shift+j/k` · `x` · `Ctrl/⌘ A` | move · extend the selection · mark · mark all |
| `Ctrl/⌘ Z` · `Ctrl/⌘ Shift Z` | undo · redo (queue, playlists, trash) |
| `/` | search on the page |
| `Shift+D` · `Shift+T` · `Ctrl/⌘ 1/2` | dense mode · light or dark · layout: preparation or live |

Each section adds its own (scoped) keys: in the Library `a` adds to the playlist (`Shift+A` after
the current song), `e` opens the editor, `m` exports an MP4, `Delete` sends to the trash; in Live
`Enter` loads the song on the player, `Shift+Enter` plays it now, `Alt+↑/↓` reorders, `s` types
the singer, `i`/`o` set the entry and exit points at the current position; in the Queue `r`
retries, `Shift+R` retries every failed job, `Delete` cancels, `Shift+P`/`Shift+C` pause and
resume, `Alt+↑/↓` change the priority. Any shortcut can be rebound in Settings by pressing the new
one; the bindings are kept on the server with the operator's other preferences.

## Fast

- Changes show at once and are confirmed by the server afterwards; if it says no, they are
  reverted with a notice. A playlist edit that meets a newer version is applied again on top.
- Undo entries go on the stack the moment the change shows, so `Ctrl+Z` right after works.
- Everything live comes through one WebSocket (`/api/events`): a snapshot, then every change.
- The browser tests measure from a key press to the change on screen: under 100 ms.

## Pieces

- `src/lib/control/`: the API client, the live store (`state.ts` is pure: one function applies
  each event), resumable uploads, notices.
- `src/lib/commands/`: shortcuts, the registry, fuzzy search, undo.
- `src/lib/shell/`: the top bar, the status bar, the palette, the cheat sheet, resizable panels,
  keyboard selection in lists, the operator's actions and preferences, intake (drop a file or
  paste a link anywhere to make a karaoke).
- `src/routes/`: `/` (the night globe), `/directo`, `/biblioteca`, `/cola`, `/workers`,
  `/saidas`, `/crear`, `/editar/[id]`, `/axustes`; `/proba-letra` is a development page for the
  lyrics component.

## Tests

```bash
pnpm --dir web lint && pnpm --dir web check && pnpm --dir web test
pnpm --dir web test:e2e   # needs Playwright's Chromium (or PLAYWRIGHT_CHROMIUM=/path)
```

The `control` project starts a v4 server with a fake worker (`e2e/control/serve.py`) and drives
the UI from the keyboard: sign in, make a karaoke, follow it, build a playlist, reorder, remove
and undo, the palette, the cheat sheet, response times and axe's WCAG 2 AA rules on every section.
The `lyrics` project compares screenshots of the lyrics component.
