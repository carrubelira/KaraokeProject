# Changelog

All notable changes to Proxecto Karaoke en Galego are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html): one version for the engine, the server
and the web app. How a release is made: [`docs/releasing.md`](docs/releasing.md).

## [Unreleased]

### Fixed

- A progress report arriving after a task was complete brought it back to life: its lease
  expired, it ran again and the console showed it stuck ("The worker stopped answering").
- The console missed changes it never heard of; now every event is numbered and a gap or a
  silent line brings a fresh snapshot.
- Outputs failed (500) when a player reported two sound outputs with the same name.
- Adding a song with no active playlist did nothing yet said it was added.

### Added

- Contracts v2: manifests of tracks by SHA-256, lyrics, nodes, orders and routing, as JSON Schema,
  TypeScript and Rust (`kp-proto`).
- `karaoke-server` v4: content store with Range and checked uploads, resumable uploads, a task
  DAG with leases and data affinity, enrolled nodes over a pinned TLS certificate, operators,
  WebSockets for players and the control.
- `karaoke-worker`: fetch, analyze, make and render tasks in a child process capped by a
  systemd scope or a Windows Job Object.
- `kp-player`: one clock for every output and screen, routing with gain and delay, pitch on the
  guide vocals and the music, calibration, outputs that come and go, a waiting screen; the
  software sync bench `kp-syncbench` and `make e2e-v4`.
- The console: a broadcast control room over a live Three.js signal field that follows the
  workers and the screens; a strip with the screen driven and its ON AIR tally, a rail of
  sections, and a deck with the transport and rotary encoders everywhere; a program monitor with
  the lyrics in sync; command palette, rebindable shortcuts, undo, and the lyrics editor
  ([`docs/web.md`](docs/web.md), decision `plan-v4/decisiones/010-consola.md`).
- Songs from a link with an analysis first: the page's metadata, a Chromaprint fingerprint looked
  up in AcoustID and MusicBrainz (language and cover), and lyrics from LRCLIB; the operator
  reviews and corrects before anything heavy runs, and can send the song straight to a screen's
  queue once it is made.
- One queue per screen (playlists are gone; a screen's playlist became its queue), so adding a
  song always has a target.
- Workers say what is happening inside them: stage and step, a live log (kept whole once the
  task ends), CPU and RAM on every system, and failures explained with what to do.


- `karaoke captions`: professional subtitles for long interviews, phrase by phrase and in sync
  with the voice, written next to each video as SRT (for DaVinci Resolve, Premiere and VLC) and
  WebVTT (for the web and archives, with who speaks), plus a short list of places to check. The
  video is only read, never written or re-encoded. Interviewer and interviewee are told apart,
  captions follow broadcast rules (two lines of 42 characters, reading speed, two-frame gaps,
  cuts between shots) and `--from-srt` brings back a subtitle file reviewed in an editor
  ([`docs/captions.md`](docs/captions.md)).
- `karaoke-bench import-lrc`: a private song's reference from its synchronised lyrics (an
  `.lrc` file, as LRCLIB has for many songs), to measure where each line starts in songs nobody
  will time word by word. The benchmark also reports a lenient WER for Galician, which does not
  count gheada, seseo, accents or pronouns written apart as mistakes.
- `karaoke-bench fetch-speech` and `karaoke-bench captions`: Galician dialogues built from
  OpenSLR 77 to measure interview captions (word errors, wrong speakers, timing, rule breaks).
- **Descargar** in the player: the song's karaoke videos, made right there with their progress
  live and kept to download (or delete) any time, plus the music without vocals, the vocals, the
  synced lyrics and the offline copy. A video made before a correction of the lyrics says so.
- The guide vocals in a video can be set from none (a karaoke) to the song as sung; each level
  is a video of its own («… (karaoke, voz 30%).mp4»).
- Downloads are named after the song («Artist - Title (karaoke).mp4», «… (sen voz).m4a»).
- `GET /api/songs/{id}/exports`, `DELETE /api/songs/{id}/exports/{name}` and
  `GET /media/{id}/{file}?download=1&name=…`.
- Lyrics can be pasted exactly as they come from any lyrics site or video description: what the
  page adds is left out before aligning — Genius's song recommendations and ticket adverts, its
  title, contributors and «Embed», credits, copyright, links and hashtags, subtitle and LRC
  timings, stage directions like «(risas)» and the song's title above the lyrics. Labels
  without brackets («CORO:», «(Estribillo x2)», «Repetir estribillo») and who sings in a duet
  («Ela: …») are understood like `[Estribillo]` headers.
- Repeats that the lyrics write once are sung as often as the song does: a couplet or a stanza
  sung several times in a row comes out each time, with or without a mark, and a mark like
  «(x4)» after a couplet repeats the couplet, not just its last line (the audio decides). Marks
  before a line («(x3) Varre vasoira») count too.
- Cyrillic and Greek letters that some lyrics sites slip into the text to spot copies («dе»
  with a Cyrillic е) are read as the Latin letters they look like.

- **A new look for the web app, «Noite»**: Galicia at night on a small planet of its own, in
  3D. Its real relief lit by the moon, its coast, the lights of its towns as they look from the
  air (population data from Kontur, CC BY 4.0) and the lighthouses of its coast sweeping the sea
  at their real rhythm. The planet sways slowly and can be taken and turned; the first time, it
  turns in from the open sea and the lights come on, cities first. It can be stopped, and holds
  still with reduced motion.
- The globe goes with you: it glides from one screen to the next and shows what each is about, a
  party with the singers' colours and rockets, or how far the karaoke being made has got.
- The songs show the one you point at big beside the list, with the line everyone knows and what
  to do with it; a song without a cover gets a sky of its own.
- New type, colours and shapes everywhere: white and the flag's sky blue on a blue-black night,
  gold for what is lit, rounded panels that let the globe show through.

### Removed

- The PWA, the browser player, party mode, device pairing, network zones and the WSL setup.

### Changed

- **v4, a distributed karaoke** ([`docs/plan-v4/`](docs/plan-v4/00-vision.md)): the server stores
  songs by content and queues the work, GPU workers on Windows or Linux take it, a native player
  for Windows and macOS plays every screen and output in sync, and a keyboard-first web control
  drives it all. There is no compatibility with v3 at run time; `karaoke package` migrates v3
  packages.
- Song stems are Opus at 48 kHz, no longer levelled when encoded: `karaoke.json` 1.3.0 carries the
  gain (`audio.gain_db`) and the player and the MP4 apply it.
- The night globe shows Galicia in its real surroundings, its neighbours in half-light.

- **Lyrics are timed by two models instead of one.** Each language's speech model now works with
  a model trained on songs in many languages, and their probabilities are averaged: each misses
  different passages. On the 79 public test songs the words within 0.3 s of where they are sung
  go from 98.8 % to 99.3 %, the mean error from 0.093 s to 0.062 s and English,
  the weakest language, from 97.6 % to 98.6 %. Aligning a 4-minute song takes about 9 s more.
- Songs in a language without a model of its own (Italian, Catalan, Basque…) are timed by the
  music model, which places 99.4 % of the words of the test songs within 0.3 s without knowing
  their language (the model used before: 91.4 %). Lyrics in a script it cannot write still go to
  the multilingual speech model.
- **Lyrics from LRCLIB are found for songs that come from a video.** The search used the video's
  title («The Rapants - Viaxei») as the song's name and found nothing, so songs the database has
  were transcribed blind. It now asks for the song's name without the artist, the kind of video
  and the guests, then tries a free search, and accepts lyrics timed for an audio up to a minute
  shorter (a video with a spoken opening or credits).
- Without lyrics, the song is transcribed in stretches of singing cut where the separated voice
  rests, instead of whole: passages a speech detector used to drop are transcribed now. Lines
  the transcriber made up, which the aligner cannot hear where they were placed, are left out.
- Better MP4 exports: songs keep their video as it came (`master.mp4`, up to 1080p, contract
  1.2.0) and the export draws on it instead of the player's 720p copy (36.9 → 43.3 dB XPSNR on a
  1080p clip, about the same time). Links now download at up to 1080p. Songs made before keep
  exporting as they did; making them again from their link adds the original.
- The «Son» panel keeps only the sound settings and the lyrics style.

### Fixed

- A one-letter word that opens a line («A avoa…» in the demo song) no longer lights up in the
  intro, seconds before its line: resting between two words of a line through a silence now has
  a small cost.
- "All" in the song filters clears the saved filter too, and only lights up when nothing is
  filtered (it used to stay lit beside "Saved" and keep showing only the saved songs).
- The download button of a finished video never showed on the create page with the real server:
  video jobs now carry their song from the start.
- Asking again for a video that was still waiting or being made queued another copy of it; it
  now gives the same job. A video waiting for the graphics card says so instead of «0 %».
- Several players following their jobs at once could get errors (500): request checks ran in
  worker threads and shared the database connection; they now run on the server's event loop.

## [3.0.0] - 2026-11-06

A rebuild from scratch, under a new name: Proxecto Karaoke en Galego. The goal stays the same — a
karaoke of any song, made for Galician first and working in any language, with lyrics that light up
exactly as they are sung — but every piece is new and every model was chosen with a benchmark.

### Added

- **Engine** (`karaoke make`): one command turns a song (file or link) into a karaoke package,
  with pasted lyrics, lyrics found on LRCLIB or none at all.
  - Vocal separation with Mel-Band RoFormer, loudness normalised to −14 LUFS.
  - Transcription with Whisper (HiTZ large-v3 for Galician, large-v3-turbo for other languages),
    voice activity detection and guards against hallucinated loops.
  - A new forced aligner with a CTC model per language (Proxecto Nós for Galician, Omnilingual
    as the fallback for some 1600 languages): word, syllable and character timings with a
    confidence per word.
  - Galician first: the language is always the one chosen, never switched silently; lyrics are
    normalised only to align (tags, repeats, numbers, apostrophes, reintegrationist spelling)
    and always shown as written; enclitic pronouns written apart are joined to their verb.
  - Backing vocals as their own lines and a colour per singer.
- **Lyrics on screen**: one layout engine in Python and TypeScript with shared test cases, pages
  and scrolling modes, a countdown after instrumental breaks and three themes with open fonts.
- **Video export** (`karaoke render`): 16:9 and 9:16 MP4 with the song's video, cover or a
  gradient behind the lyrics, title and credits, encoded with NVENC when available (a 4-minute
  song in under a minute on an RTX 3050).
- **Web app** for phone, laptop and TV: a poster library, a full-screen player (guide vocals,
  pitch, latency calibration, background video), creating a karaoke with live progress, a party
  mode where phones queue songs and act as remotes through a QR code, a lyrics and timing
  editor, offline songs and an installable app, in Galician, Spanish and English.
- **Home server** (`karaoke-server`): FastAPI with a typed OpenAPI, a job queue for one GPU with
  each job in its own process, streamed uploads, links through an always-current yt-dlp, live
  progress and time left, cancel and retry, device pairing, home and remote zones, backups,
  `doctor` and start with Windows.
- **Benchmark** (`karaoke-bench`): JamendoLyrics MultiLang (79 songs in four languages) and five
  freely licensed Galician songs, with word timing, WER, speed and memory per step and
  comparable reports in `bench/results/`.
- **Project**: one-command install (`make install`), contracts with JSON Schema and generated
  TypeScript types, a CI that runs the whole test suite with ffmpeg and a browser, licence
  checks for every dependency, `NOTICE.md`, release notes from this file and a security policy.

### Changed

- Python 3.12 with uv, SvelteKit instead of Flask templates, FastAPI instead of Flask, SQLite
  instead of Postgres, a single process instead of Celery and Redis.
- Lyrics are synchronised once in `karaoke.json` and drawn in two places (the web player and the
  MP4), instead of being burnt frame by frame into a video.

### Removed

- Demucs, the WhisperX service, MoviePy, PIL and ImageMagick rendering, Docker Compose, Celery,
  Redis, Postgres, Cloudflare R2, Fly.io, Sentry and email magic links. The previous system is
  kept at the `v2-final` tag.

### Measured

- With lyrics, JamendoLyrics MultiLang (79 songs): 98.8 % of words start within 0.3 s of the
  reference (mean error 0.093 s); Galician set: 99.8 %.
- Without lyrics: 23.2 % word error rate on JamendoLyrics (33.7 % for a Demucs + Whisper
  large-v3-turbo baseline) and 26.5 % on the Galician songs with published lyrics (35.9 %).
- No silent language switch in the whole benchmark.
- A 4:47 song with lyrics is ready in about 85 s on an RTX 3050 Laptop with 4 GB.

## [2.0.0] - 2026-06-03

The second system, kept at the `v2-final` tag: Flask web app with a Galician, Spanish and
English interface, Celery workers for Demucs and WhisperX, Postgres with Alembic, storage on
Cloudflare R2, email sign-in and a deployment to Fly.io that was never put live.

## [1.1.0] - 2026-05-29

Security fixes before making the repository public.

## [1.0.0] - 2025-10-31

The bachelor's thesis (TFG) at the Universidade da Coruña: Docker microservices with Demucs,
WhisperX and MoviePy, and a Flask web app. The thesis is in [`docs/tfg/`](docs/tfg/).

[Unreleased]: https://github.com/gaelfernandez1/KaraokeProject/compare/v3.0.0...HEAD
[3.0.0]: https://github.com/gaelfernandez1/KaraokeProject/compare/v2-final...v3.0.0
[2.0.0]: https://github.com/gaelfernandez1/KaraokeProject/compare/v1.1-pre-restructure...v2-final
[1.1.0]: https://github.com/gaelfernandez1/KaraokeProject/compare/v1.0-tfg...v1.1-pre-restructure
[1.0.0]: https://github.com/gaelfernandez1/KaraokeProject/releases/tag/v1.0-tfg
