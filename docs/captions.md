# Interview captions

Professional subtitles for long recorded interviews: phrase by phrase, in sync with the voice, and
written next to the video, which is never touched. The decision is in
[`plan-v3/decisiones/018-subtitulos-entrevistas.md`](plan-v3/decisiones/018-subtitulos-entrevistas.md)
(in Spanish).

```bash
uv run karaoke captions /mnt/d/interviews/xan            # every video in the folder
uv run karaoke captions MVI_0704.MP4 MVI_0705.MP4             # or the files
uv run karaoke captions --from-srt MVI_0704.gl.srt            # after reviewing it in an editor
```

Next to each video it writes three files:

| File | What it is |
|---|---|
| `<name>.gl.srt` | the subtitles for editors and players (DaVinci Resolve, Premiere, VLC): UTF-8 with a byte order mark and CRLF line ends, which Windows tools read without mangling accents |
| `<name>.gl.vtt` | the same in WebVTT, for the web and the archive: a `NOTE` says how and when it was made, and `<v Entrevistado>` / `<v Entrevistador>` says who speaks |
| `<name>.gl.revisar.txt` | a short list of places worth a second look, with the editor's timecode (`HH:MM:SS:FF`) and the time in seconds |

Options: `--lang` (default `gl`), `--force` (redo subtitles that exist; the old SRT is kept as
`.srt.bak`, then `.srt.bak2` and so on, so a review is never lost), `--no-shots` (do not look for cuts), `--audio-track N` (from 1; by default the track
marked as default, or the first), `--model` (a Whisper model from
[`languages-and-models.md`](languages-and-models.md)).

## The video is never modified

- It is only opened for reading. One ffmpeg reads just its audio and writes the speech track
  (16 kHz mono FLAC) to `~/.cache/karaoke/captions/`: about 30 times real time for a 4K interview
  on a USB disk. Unless `--no-shots`, a second ffmpeg finds the cuts between shots while Whisper
  transcribes, decoding the picture on the graphics card (NVDEC) or, if that fails, the processor:
  about 6 times real time, so doing it at the same time keeps it off the total.
- Nothing else is written next to it: the three files are written under hidden side names and
  only take theirs when all three are ready, so an interrupted run or an unplugged disk never
  leaves half a file.
- An existing `<name>.gl.srt` is never overwritten without `--force`: it may hold a review.
- Tests check the video's SHA-256, size and modification time before and after.

Cached work (the speech track, the transcript) is keyed by the file's path, size and date and
by the version of each step, so running again after a stop resumes where it was.

## How the subtitles are made

1. **Speech**: Whisper with word times (`word_timestamps`, beam of one), in the language asked
   for, with the Galician model for Galician (`captions/speech.py`), given the audio in pieces of
   up to ten minutes cut in silences. Speech regions come from Silero's voice
   detector, bundled with faster-whisper. Text where nobody speaks, loops, and the stock phrases
   Whisper learnt from subtitled videos ("Subtítulos realizados por la comunidad de Amara.org",
   "Gracias por ver") are dropped and listed for review. Punctuation Whisper glues to the front of
   the next word (".E") goes back to the word it closes.
2. **Word times** (`captions/refine.py`): Whisper's word times run early (captions came in
   0.39 s before the voice on the bench), so the words it heard are placed again by the CTC
   aligner the karaoke uses for lyrics (wav2vec2, the Galician model for Galician): emissions
   worked out once for the recording, then each stretch of words between pauses aligned on its
   own slice. A word the aligner is unsure of, or that would move more than a second, keeps
   Whisper's time.
3. **Who speaks** (`captions/speakers.py`): each stretch of speech is cut into 1.5 s windows
   every 0.75 s, each window gets a voice print from WeSpeaker's ResNet34 (ONNX, on the
   processor), and the prints split into two groups by direction. The group that talks more is
   the interviewee (`A`), the other the interviewer (`B`); two groups pointing the same way are
   one voice. A "turn" of less than a second inside someone else's answer is taken as a mistake.
4. **Captions** (`captions/segment.py`): words gather while they fit in two lines and seven
   seconds without a line ending on a word that leans on the next one. A change of speaker, or a
   sentence that ends before a pause, always starts a new caption. Otherwise the cut goes, in
   order of preference, to a sentence end, a pause of 0.3 s or more, a comma, or before a
   conjunction, never right after a word that leans on the next one (an article, a preposition,
   an unstressed pronoun), and never leaving a piece under 12 characters except where a sentence
   ends. A short question and its short answer share a caption, a line each with a dash:
   `-¿E logo?` / `-Pois si.`
5. **Lines** (`captions/lines.py`): one line if it fits; otherwise the best break: never after
   such a word, preferably after punctuation, the lower line longer.
6. **Timing** (`captions/timing.py`), in whole frames: a caption comes in with its first word,
   or on a cut within twelve frames; stays up to half a second after its last word; lasts at
   least 5/6 s; closes a gap under half a second to two frames (no flicker between chained
   captions), also after being lengthened; ends two frames before a nearby cut unless that would
   hide words still being said; and never overlaps another, even when two people talk at once.

The rules (`captions/rules.py`) follow the Netflix timed text style guides (general and
Castilian Spanish) and the Spanish standard UNE 153010:

| Rule | Value |
|---|---|
| Lines per caption | 1 or 2 |
| Characters per line | at most 42 |
| Reading speed | aim at 15 characters per second; the review list counts those over 17 and lists those over 25 |
| Duration | from 5/6 s to 7 s |
| Gap between captions | at least 2 frames; under 0.5 s it closes to 2 frames |
| Out time | up to 0.5 s after the last word |
| Cuts | an edge within 12 frames of a cut moves to it |

The text is what the model writes: standard spelling with the speaker's own words. Galician
*gheada* and *seseo* are not written. Spontaneous speech often runs at 17 to 25 characters a
second; it stays word for word (it is a testimony).

The review list is short on purpose, because the interview is watched in full anyway. It lists
content words Whisper was very unsure of (under 0.15; it is always unsure of a segment's first
"Que" or "E", which are left out), captions over 25 characters a second, long stretches of voice
with no text, text the guards threw away, and changes of speaker where the voice prints blur.

## How well it does

On the bench (`karaoke-bench captions --pipeline bench/pipelines/captions-default.toml`): 12
Galician dialogues of about five minutes made from OpenSLR 77 sentences (read speech, CC BY-SA
4.0), an interviewer asking briefly and an interviewee answering at length, half of them with two
voices of the same gender ([benchmark guide](benchmark.md)).

| Measure | Value |
|---|---|
| Words wrong (WER) | 7.3 % |
| Words given to the wrong speaker | 0.0 % |
| Caption in-time against the voice: median · 90th percentile | 0.05 s · 0.26 s (Whisper's own word times: 0.39 s · 0.81 s, early) |
| Captions breaking a rule (lines, characters, overlaps, gaps) | 0 |

Other settings measured, in [decision 018](plan-v3/decisiones/018-subtitulos-entrevistas.md):
HiTZ with a beam of 5 gives the same words in twice the time; Proxecto Nós's turbo model makes
7.6 % of the words wrong in half the time (`--model nos-turbo-gl`), and large-v3-turbo 15.2 %.
HiTZ stays the default because on harder real speech (the Galician songs of decision 005) it was
ten points ahead of Nós. Read speech is cleaner than an interview in
a kitchen with gheada and seseo: on the real ones expect more wrong words, which is what the
watch-through is for.

## Speed and memory

Measured on the RTX 3050 (4 GB) with WSL's 7.6 GB of RAM, on six 4K interviews from a camera (2 h
50 min, H.264 at 57 Mbit/s) read from a USB disk: **about 10 minutes per hour of interview**.

| Step | Per hour | Memory |
|---|---|---|
| Reading the audio | about 2 min | little |
| Transcribing, in pieces of up to 10 min (the cuts are found at the same time) | about 5 min | 3.3 GB of RAM, 2.4 GB of graphics memory |
| Word times from the aligner | about 2 min | under 1 GB of graphics memory |
| Telling the voices apart (on the processor) | about 1.5 min | 1 GB of RAM |

One step with a model at a time. Whisper gets the audio in pieces cut in silences because it holds
the spectrogram of everything it is given: a whole hour at once took the process past 5 GB.

## Reviewing in DaVinci Resolve

1. Make a **new timeline from the delivered file** (the one next to the subtitles, not the
   original edit) and set its **start timecode to `00:00:00:00`**. DaVinci starts timelines at
   `01:00:00:00`; with interviews longer than an hour, an hour's offset is easy to miss.
2. Import `<name>.gl.srt` onto a subtitle track.
3. Watch it through, with the review list at hand, and correct on the track.
4. Export **only the subtitle track** as SRT over `<name>.gl.srt`. Do not render the video.
5. `uv run karaoke captions --from-srt <name>.gl.srt` rebuilds the WebVTT with the reviewed text
   (keeping who speaks from the generated captions it overlaps) and a new review list that flags
   edits breaking the rules (long lines, more than two lines, overlaps). If most captions moved by
   the same amount (the timeline was not at `00:00:00:00`), or the last one ends after the video,
   it writes nothing and says so. The SRT must sit next to the video with the video's name
   (DaVinci suggests `Timeline 1.srt`): without the video its times cannot be checked, so it is
   refused.

## What it does not do

- It does not burn subtitles into the picture or add a subtitle track to the video: either would
  mean writing a new video file. Players show the SRT or WebVTT next to it.
- It does not translate.
- It does not name the people who speak; the WebVTT labels them `Entrevistado` and
  `Entrevistador`.
