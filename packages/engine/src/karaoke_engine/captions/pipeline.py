"""`karaoke captions`: from an interview video to SRT, WebVTT and a review list beside it.

The video is read once (source.py) and never written. The heavy work (the speech track, the
transcript) is cached under ~/.cache/karaoke/captions, keyed by the file and the step versions,
so a run that stops resumes where it was. The three files next to the video are written aside
and only take their names when all three are ready: an unplugged disk never leaves half a file.
A reviewed SRT (edited in DaVinci Resolve) comes back with --from-srt to rebuild the WebVTT.
"""

import contextlib
import datetime
import json
import shutil
import subprocess
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from karaoke_engine.captions import speech as speech_step
from karaoke_engine.captions.formats import SRT_ENCODING, read_srt, to_srt, to_vtt
from karaoke_engine.captions.review import format_review, review_items
from karaoke_engine.captions.rules import Caption, Rules, TimedWord
from karaoke_engine.captions.segment import group_captions
from karaoke_engine.captions.source import cache_key, probe_source, read_source
from karaoke_engine.captions.speech import SpeechTranscript
from karaoke_engine.captions.timing import cps, time_captions

VIDEO_EXTENSIONS = frozenset({".mp4", ".mov", ".mkv", ".mxf", ".avi", ".m4v", ".mts"})
# Bumped when a step's output changes, so cached work is redone.
READ_VERSION = "1"
SPEECH_VERSION = "2"
# Speech this long with no word in it goes to the review list.
_MISSED_SECONDS = 2.0
# A reviewed SRT whose captions mostly moved by the same amount was exported from a timeline
# that does not start where the video does (DaVinci starts at 01:00:00:00).
_OFFSET_SHARE = 0.8
_OFFSET_MIN = 1.0
_ERRORS = (OSError, ValueError, RuntimeError, MemoryError, subprocess.SubprocessError)

Step = Callable[[Path, SpeechTranscript], SpeechTranscript]
Progress = Callable[[str, float], None]


@dataclass
class CaptionOptions:
    language: str = "gl"
    force: bool = False
    shots: bool = True
    audio_track: int | None = None  # from 0
    model: str = "auto"
    rules: Rules = field(default_factory=Rules)
    low_confidence: float = 0.3
    cache: Path = field(default_factory=lambda: Path.home() / ".cache" / "karaoke" / "captions")
    steps: Sequence[Step] = ()
    transcribe: Callable[..., SpeechTranscript] | None = None  # transcribe_speech_in_child
    labels: Mapping[str, str] = field(
        default_factory=lambda: {"A": "Entrevistado", "B": "Entrevistador"}
    )


@dataclass(frozen=True)
class CaptionResult:
    video: Path
    outputs: tuple[Path, ...] = ()
    captions: int = 0
    to_review: int = 0
    elapsed: float = 0.0
    skipped: str | None = None
    error: str | None = None


def find_videos(paths: Sequence[Path]) -> list[Path]:
    """The videos to caption: files as given, and the videos directly inside folders."""
    found: list[Path] = []
    for path in paths:
        if path.is_dir():
            found += sorted(
                (p for p in path.iterdir() if p.is_file() and _is_video(p)),
                key=lambda p: p.name.lower(),
            )
        else:
            found.append(path)
    return found


def outputs_for(video: Path, language: str) -> tuple[Path, Path, Path]:
    """The SRT, WebVTT and review list that go next to a video."""
    base = f"{video.stem}.{language}"
    return (
        video.with_name(f"{base}.srt"),
        video.with_name(f"{base}.vtt"),
        video.with_name(f"{base}.revisar.txt"),
    )


def caption_all(
    paths: Sequence[Path],
    options: CaptionOptions,
    progress: Callable[[int, int, Path, str, float], None] | None = None,
) -> list[CaptionResult]:
    """Captions every video in turn; one that fails is reported and the rest go on."""
    videos = find_videos(paths)
    results: list[CaptionResult] = []
    for n, video in enumerate(videos, 1):
        started = time.monotonic()

        def report(step: str, done: float, n: int = n, video: Path = video) -> None:
            if progress is not None:
                progress(n, len(videos), video, step, done)

        try:
            results.append(caption_video(video, options, report))
        except _ERRORS as exc:
            results.append(
                CaptionResult(
                    video, elapsed=time.monotonic() - started, error=str(exc) or repr(exc)
                )
            )
    return results


def caption_video(
    video: Path, options: CaptionOptions, progress: Progress | None = None
) -> CaptionResult:
    started = time.monotonic()
    report = progress or (lambda _step, _done: None)
    srt, vtt, review = outputs_for(video, options.language)
    if srt.exists() and not options.force:
        return CaptionResult(video, skipped=f"{srt.name} already exists (--force redoes it)")
    info = probe_source(video, options.audio_track)
    work = options.cache / cache_key(info, "read", READ_VERSION, f"a{info.audio_index}")
    work.mkdir(parents=True, exist_ok=True)
    audio, shots_file = work / "audio.flac", work / f"shots-{options.shots}.json"
    if not (audio.is_file() and shots_file.is_file()):
        report("read", 0.0)
        cuts = read_source(
            info, audio, shots=options.shots, on_progress=lambda d: report("read", d)
        )
        _write_json(shots_file, cuts)
    cuts = json.loads(shots_file.read_text())

    report("transcribe", 0.0)
    transcript = _transcript(audio, work, options)
    for step in options.steps:
        transcript = step(audio, transcript)
    report("write", 0.0)
    rules = options.rules
    captions = time_captions(
        group_captions(transcript.words, rules), rules, info.fps, cuts, info.duration
    )
    items = review_items(
        captions, rules, low_confidence=options.low_confidence,
        missed=_missed(transcript.speech, transcript.words), dropped=transcript.dropped,
    )  # fmt: skip
    elapsed = time.monotonic() - started
    note = f"Subtítulos automáticos, sin revisar.\nModelo: {transcript.model}.\nFecha: {_today()}."
    listed = format_review(
        items,
        video=video.name,
        captions=len(captions),
        fps=info.fps,
        elapsed=elapsed,
        fast=sum(cps(c) > rules.max_cps for c in captions),
        max_cps=rules.max_cps,
    )
    files = {
        srt: (to_srt(captions), SRT_ENCODING),
        vtt: (to_vtt(captions, note, options.labels), "utf-8"),
        review: (listed, "utf-8"),
    }
    _write_all(files, backup=srt if options.force else None)
    _write_json(_generated(options.cache, info), [asdict(c) | {"words": []} for c in captions])
    report("write", 1.0)
    return CaptionResult(video, (srt, vtt, review), len(captions), len(items), elapsed)


def caption_audio(
    audio: Path, language: str, options: CaptionOptions, fps: float = 25.0
) -> tuple[list[Caption], SpeechTranscript]:
    """The captions of a sound file, as a video's would be (for the bench); nothing is cached."""
    transcribe = options.transcribe or speech_step.transcribe_speech_in_child
    transcript = transcribe(audio, language, model=options.model)
    for step in options.steps:
        transcript = step(audio, transcript)
    rules = options.rules
    return time_captions(group_captions(transcript.words, rules), rules, fps), transcript


def rebuild_from_srt(srt: Path, options: CaptionOptions) -> CaptionResult:
    """The WebVTT and review list again, from an SRT reviewed in an editor."""
    started = time.monotonic()
    suffix = f".{options.language}.srt"
    base = srt.name[: -len(suffix)] if srt.name.endswith(suffix) else srt.stem
    video = next((p for p in sorted(srt.parent.iterdir()) if p.stem == base and _is_video(p)), None)
    try:
        captions = read_srt(srt.read_text(encoding=SRT_ENCODING))
        fps, generated = 25.0, None
        if video is not None:
            info = probe_source(video)
            fps = info.fps
            generated = _load_generated(_generated(options.cache, info))
            _check_offset(captions, generated, info.duration)
        if generated:
            captions = _with_speakers(captions, generated)
        _, vtt, review = outputs_for(srt.parent / f"{base}.x", options.language)
        items = review_items(captions, options.rules, low_confidence=options.low_confidence)
        note = f"Subtítulos revisados por una persona ({srt.name}).\nFecha: {_today()}."
        elapsed = time.monotonic() - started
        _write_all({
            vtt: (to_vtt(captions, note, options.labels), "utf-8"),
            review: (
                format_review(items, video=video.name if video else srt.name,
                              captions=len(captions), fps=fps, elapsed=elapsed),
                "utf-8",
            ),
        })  # fmt: skip
    except _ERRORS as exc:
        return CaptionResult(srt, elapsed=time.monotonic() - started, error=str(exc))
    return CaptionResult(srt, (vtt, review), len(captions), len(items), elapsed)


def _transcript(audio: Path, work: Path, options: CaptionOptions) -> SpeechTranscript:
    cached = work / f"speech-{options.language}-{options.model}-{SPEECH_VERSION}.json"
    if cached.is_file():
        return _transcript_from(json.loads(cached.read_text(encoding="utf-8")))
    transcribe = options.transcribe or speech_step.transcribe_speech_in_child
    transcript = transcribe(audio, options.language, model=options.model)
    _write_json(cached, asdict(transcript))
    return transcript


def _transcript_from(data: dict[str, Any]) -> SpeechTranscript:
    return SpeechTranscript(
        words=tuple(TimedWord(**w) for w in data["words"]),
        speech=tuple((float(a), float(b)) for a, b in data["speech"]),
        dropped=tuple((float(a), float(b), str(t)) for a, b, t in data["dropped"]),
        model=data["model"],
    )


def _missed(
    speech: Sequence[tuple[float, float]], words: Sequence[TimedWord]
) -> list[tuple[float, float]]:
    """Long stretches of speech with no word in them: text Whisper may have lost."""
    middles = sorted((w.start + w.end) / 2 for w in words)
    return [
        (a, b)
        for a, b in speech
        if b - a >= _MISSED_SECONDS and not any(a <= m <= b for m in middles)
    ]


def _check_offset(
    captions: Sequence[Caption], generated: Sequence[Caption] | None, duration: float
) -> None:
    if generated:
        shifts = [round(e.start - g.start, 1) for e, g in zip(captions, generated, strict=False)]
        common = max(set(shifts), key=shifts.count) if shifts else 0.0
        if abs(common) >= _OFFSET_MIN and shifts.count(common) >= _OFFSET_SHARE * len(shifts):
            raise ValueError(
                f"the subtitles are {common:+.0f} s away from the ones generated: was the "
                "timeline starting at 01:00:00:00? Set it to 00:00:00:00 and export again"
            )
    if captions and duration > 0 and captions[-1].end > duration + 1.0:
        raise ValueError(
            f"the last subtitle ends at {captions[-1].end:.0f} s and the video lasts "
            f"{duration:.0f} s: was the timeline starting at 01:00:00:00?"
        )


def _with_speakers(captions: Sequence[Caption], generated: Sequence[Caption]) -> list[Caption]:
    """Who speaks in each reviewed caption, from the generated one it overlaps most."""
    out: list[Caption] = []
    for caption in captions:
        best = max(
            generated,
            key=lambda g: min(g.end, caption.end) - max(g.start, caption.start),
        )
        overlap = min(best.end, caption.end) - max(best.start, caption.start)
        speakers = caption.speakers
        if overlap > 0 and len(best.speakers) == len(caption.lines):
            speakers = best.speakers
        elif overlap > 0 and len(set(best.speakers)) == 1:
            speakers = (best.speakers[0],) * len(caption.lines)
        out.append(Caption(caption.start, caption.end, caption.lines, speakers))
    return out


def _generated(cache: Path, info: Any) -> Path:
    return cache / "generated" / f"{cache_key(info, 'generated')}.json"


def _load_generated(path: Path) -> list[Caption] | None:
    if not path.is_file():
        return None
    return [
        Caption(c["start"], c["end"], tuple(c["lines"]), tuple(c["speakers"]))
        for c in json.loads(path.read_text(encoding="utf-8"))
    ]


def _write_all(files: Mapping[Path, tuple[str, str]], backup: Path | None = None) -> None:
    """Writes every file aside, then gives them their names; on failure, none is left."""
    parts = {target: target.with_name(f".{target.name}.part") for target in files}
    try:
        for target, (text, encoding) in files.items():
            _write_part(parts[target], text, encoding)
        if backup is not None and backup.exists():
            shutil.copy2(backup, backup.with_name(backup.name + ".bak"))
        for target, part in parts.items():
            part.replace(target)
    finally:
        for part in parts.values():
            with contextlib.suppress(OSError):
                part.unlink(missing_ok=True)


def _write_part(path: Path, text: str, encoding: str) -> None:
    path.write_text(text, encoding=encoding, newline="")


def _write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    side = path.with_name(path.name + ".part")
    side.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    side.replace(path)


def _is_video(path: Path) -> bool:
    return path.suffix.lower() in VIDEO_EXTENSIONS and not path.name.startswith(".")


def _today() -> str:
    return datetime.datetime.now(tz=datetime.UTC).date().isoformat()
