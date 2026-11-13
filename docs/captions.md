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
`.srt.bak`), `--no-shots` (do not look for cuts), `--audio-track N` (from 1; by default the track
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

1. **Speech**: Whisper with word times (`word_timestamps`), in the language asked for, with the
   Galician model for Galician (`captions/speech.py`). Speech regions come from Silero's voice
   detector, bundled with faster-whisper. Text where nobody speaks, loops, and the stock phrases
   Whisper learnt from subtitled videos ("Subtítulos realizados por la comunidad de Amara.org",
   "Gracias por ver") are dropped and listed for review.
2. **Captions** (`captions/segment.py`): words gather while they fit in two lines and seven
   seconds. A change of speaker, or a sentence that ends before a pause, always starts a new
   caption. Otherwise the cut goes, in order of preference, to a sentence end, a pause of 0.3 s or
   more, a comma, or before a conjunction, and never right after a word that leans on the next
   one (an article, a preposition, an unstressed pronoun). A short question and its short answer
   share a caption, a line each with a dash: `-¿E logo?` / `-Pois si.`
3. **Lines** (`captions/lines.py`): one line if it fits; otherwise the best break: never after
   such a word, preferably after punctuation, the lower line longer.
4. **Timing** (`captions/timing.py`), in whole frames: a caption comes in with its first word,
   or on a cut within twelve frames; stays up to half a second after its last word; closes a
   gap under half a second to two frames (no flicker between chained captions); ends two frames
   before a nearby cut unless that would hide words still being said; lasts at least 5/6 s; and
   never overlaps another, even when two people talk at once.

The rules (`captions/rules.py`) follow the Netflix timed text style guides (general and
Castilian Spanish) and the Spanish standard UNE 153010:

| Rule | Value |
|---|---|
| Lines per caption | 1 or 2 |
| Characters per line | at most 42 |
| Reading speed | aim at 15 characters per second; over 17 goes to the review list |
| Duration | from 5/6 s to 7 s |
| Gap between captions | at least 2 frames; under 0.5 s it closes to 2 frames |
| Out time | up to 0.5 s after the last word |
| Cuts | an edge within 12 frames of a cut moves to it |

The text is what the model writes: standard spelling with the speaker's own words. Galician
*gheada* and *seseo* are not written. Fast speech stays word for word (it is a testimony) and goes
to the review list.

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
   it writes nothing and says so.

## What it does not do

- It does not burn subtitles into the picture or add a subtitle track to the video: either would
  mean writing a new video file. Players show the SRT or WebVTT next to it.
- It does not translate.
- It does not name the people who speak; the WebVTT labels them `Entrevistado` and
  `Entrevistador`.
