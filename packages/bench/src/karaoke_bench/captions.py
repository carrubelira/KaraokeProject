"""Measuring interview captions on Galician dialogues whose words, turns and times are known.

There is no public Galician interview with timed subtitles, so the set is made: sentences read by
volunteers (OpenSLR 77, Google's crowdsourced Galician speech, CC BY-SA 4.0, with the speaker in
each file name) are joined into dialogues of about five minutes. An "interviewer" (B) says one or
two sentences, an "interviewee" (A) three to eight, with the pauses of real speech between them;
half the dialogues pair two voices of the same gender, the harder case for telling them apart.
Each sentence's text, speaker and where its voice starts and ends are the reference.

It is read speech, cleaner than an interview recorded in a kitchen: the numbers compare models
and settings with each other; how the real interviews read is judged by watching them.
"""

import datetime
import functools
import hashlib
import json
import random
import resource
import statistics
import time
import tomllib
import zipfile
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt

from karaoke_bench.fetch import http_download
from karaoke_bench.metrics import text_errors
from karaoke_bench.paths import BenchPaths
from karaoke_bench.resources import GpuSampler
from karaoke_bench.textnorm import tokens
from karaoke_engine.align.audio import load_mono16k
from karaoke_engine.captions.pipeline import (
    SPEAKERS_VERSION,
    SPEECH_VERSION,
    CaptionOptions,
    caption_audio,
    transcript_from,
)
from karaoke_engine.captions.rules import Caption, Rules, TimedWord
from karaoke_engine.captions.speakers import speakers_in_child
from karaoke_engine.captions.speech import SpeechTranscript, transcribe_speech_in_child
from karaoke_engine.captions.timing import cps

SLR77 = "https://openslr.elda.org/resources/77/"
SLR77_FILES = (
    "LICENSE",
    "line_index_female.tsv",
    "line_index_male.tsv",
    "gl_es_female.zip",
    "gl_es_male.zip",
)
SAMPLE_RATE = 16000
_B_SENTENCES = (1, 2)
_A_SENTENCES = (3, 8)
_PAUSE_IN_TURN = (0.2, 1.5)
_PAUSE_BETWEEN_TURNS = (0.1, 1.0)
# A caption starting this far from a sentence does not count as that sentence's caption.
_ONSET_REACH = 2.0
_SILENCE_DB = -40.0


@dataclass(frozen=True)
class Clip:
    speaker: str
    gender: str  # "female" or "male"
    file: str  # file id, without the extension
    text: str
    seconds: float


@dataclass(frozen=True)
class Part:
    role: str  # "B" asks, "A" answers
    clip: Clip
    pause: float  # silence before it


@dataclass(frozen=True)
class DialoguePlan:
    name: str
    parts: tuple[Part, ...]


@dataclass(frozen=True)
class RefUtterance:
    start: float
    end: float
    text: str
    speaker: str


@dataclass(frozen=True)
class CaptionMetrics:
    wer: float
    speaker_word_error: float | None
    onset_error_median: float | None
    onset_error_p90: float | None
    onset_missing: int
    captions: int
    violations: dict[str, int] = field(default_factory=dict)
    # Caption start minus voice start, for each sentence that opens a caption (negative: early).
    onsets: tuple[float, ...] = ()


def plan_dialogues(
    clips: Sequence[Clip], *, count: int = 12, seconds: float = 300.0, seed: int = 0
) -> list[DialoguePlan]:
    """Which sentences each dialogue joins, who says them and the pauses: the same for a seed."""
    rng = random.Random(seed)  # noqa: S311 - a reproducible sample, not a secret
    by_speaker: dict[str, list[Clip]] = {}
    for clip in sorted(clips, key=lambda c: c.file):
        by_speaker.setdefault(clip.speaker, []).append(clip)
    genders = {
        g: sorted(s for s, c in by_speaker.items() if c[0].gender == g) for g in ("female", "male")
    }
    plans: list[DialoguePlan] = []
    for n in range(count):
        if n % 2 == 0:
            gender = "female" if n % 4 == 0 else "male"
            interviewer, interviewee = rng.sample(genders[gender], 2)
        else:
            pair = [rng.choice(genders["female"]), rng.choice(genders["male"])]
            rng.shuffle(pair)
            interviewer, interviewee = pair
        pools = {
            "B": rng.sample(by_speaker[interviewer], len(by_speaker[interviewer])),
            "A": rng.sample(by_speaker[interviewee], len(by_speaker[interviewee])),
        }
        parts: list[Part] = []
        total, role = 0.0, "B"
        while total < seconds and pools[role]:
            low, high = _B_SENTENCES if role == "B" else _A_SENTENCES
            for k in range(rng.randint(low, high)):
                if not pools[role]:
                    break
                clip = pools[role].pop()
                if not parts:
                    pause = 0.0
                elif k == 0:
                    pause = round(rng.uniform(*_PAUSE_BETWEEN_TURNS), 2)
                else:
                    pause = round(rng.uniform(*_PAUSE_IN_TURN), 2)
                parts.append(Part(role, clip, pause))
                total += pause + clip.seconds
            role = "A" if role == "B" else "B"
        plans.append(DialoguePlan(f"dialogue-{n + 1:02d}", tuple(parts)))
    return plans


def render_dialogue(
    plan: DialoguePlan, audio_of: Callable[[Clip], npt.NDArray[np.float32]], out: Path
) -> list[RefUtterance]:
    """Writes the dialogue as a 16 kHz WAV and returns where each sentence's voice is."""
    import wave

    pieces: list[npt.NDArray[np.float32]] = []
    reference: list[RefUtterance] = []
    t = 0.0
    for part in plan.parts:
        silence = np.zeros(round(part.pause * SAMPLE_RATE), dtype=np.float32)
        samples = audio_of(part.clip)
        start, end = speech_bounds(samples, SAMPLE_RATE)
        t += len(silence) / SAMPLE_RATE
        reference.append(
            RefUtterance(round(t + start, 3), round(t + end, 3), part.clip.text, part.role)
        )
        t += len(samples) / SAMPLE_RATE
        pieces += [silence, samples]
    audio = np.concatenate(pieces) if pieces else np.zeros(0, dtype=np.float32)
    out.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes((np.clip(audio, -1, 1) * 32767).astype("<i2").tobytes())
    return reference


def speech_bounds(samples: npt.NDArray[np.float32], rate: int = SAMPLE_RATE) -> tuple[float, float]:
    """Where the voice of a clean clip starts and ends: frames within 40 dB of its loudest."""
    hop = round(0.01 * rate)
    count = len(samples) // hop
    if count == 0:
        return 0.0, len(samples) / rate
    frames = samples[: count * hop].reshape(count, hop).astype(np.float64)
    level = 20 * np.log10(np.sqrt((frames**2).mean(axis=1)) + 1e-10)
    loud = np.flatnonzero(level >= level.max() + _SILENCE_DB)
    return float(loud[0] * hop / rate), float((loud[-1] + 1) * hop / rate)


def caption_metrics(
    reference: Sequence[RefUtterance],
    captions: Sequence[Caption],
    words: Sequence[TimedWord],
    rules: Rules,
    fps: float,
) -> CaptionMetrics:
    said = " ".join(u.text for u in reference)
    written = " ".join(" ".join(c.lines) for c in captions).replace("-", " ")
    onsets, opened = _onsets(reference, captions)
    turns = [
        i for i in range(1, len(reference)) if reference[i].speaker != reference[i - 1].speaker
    ]
    missing = sum(i not in opened for i in turns)
    errors = [abs(o) for o in onsets]
    return CaptionMetrics(
        wer=round(text_errors(said, written).wer, 4),
        speaker_word_error=_speaker_error(reference, words),
        onset_error_median=round(statistics.median(errors), 3) if errors else None,
        onset_error_p90=round(_percentile(errors, 0.9), 3) if errors else None,
        onset_missing=missing,
        captions=len(captions),
        violations=violations(captions, rules, fps),
        onsets=tuple(onsets),
    )


def _onsets(
    reference: Sequence[RefUtterance], captions: Sequence[Caption]
) -> tuple[list[float], set[int]]:
    """For each caption that starts where a sentence starts (its first word, within reach), how
    far its start is from that sentence's voice; and which sentences open a caption."""
    firsts = [(tokens(u.text) or [""])[0] for u in reference]
    onsets: list[float] = []
    opened: set[int] = set()
    for caption in captions:
        first = (tokens(" ".join(caption.lines)) or [""])[0]
        near = [
            i
            for i, u in enumerate(reference)
            if i not in opened
            and firsts[i] == first
            and abs(caption.start - u.start) <= _ONSET_REACH
        ]
        if near:
            i = min(near, key=lambda i: abs(caption.start - reference[i].start))
            opened.add(i)
            onsets.append(round(caption.start - reference[i].start, 3))
    return onsets, opened


def violations(captions: Sequence[Caption], rules: Rules, fps: float) -> dict[str, int]:
    """How many captions break each rule."""
    counts = dict.fromkeys(("lines", "chars", "cps", "short", "long", "overlap", "gap"), 0)
    gap = rules.min_gap_frames / fps
    previous: Caption | None = None
    for caption in captions:
        length = caption.end - caption.start
        counts["lines"] += len(caption.lines) > rules.max_lines
        counts["chars"] += any(len(line) > rules.max_chars for line in caption.lines)
        counts["cps"] += cps(caption) > rules.max_cps
        counts["short"] += length < rules.min_duration - 1e-6
        counts["long"] += length > rules.max_duration + 1e-6
        if previous is not None:
            counts["overlap"] += caption.start < previous.end - 1e-6
            counts["gap"] += 0 <= caption.start - previous.end < gap - 1e-6
        previous = caption
    return counts


def fetch_speech(paths: BenchPaths, download: Callable[[str, Path], None] = http_download) -> Path:
    """Downloads and unpacks OpenSLR 77 into bench/data/speech-gl/slr77 (once)."""
    folder = paths.data / "speech-gl" / "slr77"
    for name in SLR77_FILES:
        target = folder / name
        if not target.is_file():
            download(SLR77 + name, target)
        if name.endswith(".zip") and not (folder / name.removesuffix(".zip")).is_dir():
            with zipfile.ZipFile(target) as archive:
                archive.extractall(folder / name.removesuffix(".zip"))
    return folder


def load_clips(folder: Path) -> list[Clip]:
    """The sentences of OpenSLR 77, with their speaker, gender, text and length."""
    import wave

    wavs = {p.stem: p for p in folder.rglob("*.wav")}
    clips: list[Clip] = []
    for gender in ("female", "male"):
        index = folder / f"line_index_{gender}.tsv"
        for row in index.read_text(encoding="utf-8").splitlines():
            file, _, text = row.partition("\t")
            path = wavs.get(file.strip())
            if path is None or not text.strip():
                continue
            with wave.open(str(path)) as wav:
                seconds = wav.getnframes() / wav.getframerate()
            speaker = file.rsplit("_", 1)[0]
            clips.append(Clip(speaker, gender, file.strip(), text.strip(), round(seconds, 3)))
    return clips


def build_set(paths: BenchPaths, *, count: int = 12, seconds: float = 300.0, seed: int = 0) -> Path:
    """Downloads OpenSLR 77 if needed and writes the dialogues (WAV and reference JSON)."""
    folder = fetch_speech(paths)
    clips = load_clips(folder)
    wavs = {p.stem: p for p in folder.rglob("*.wav")}
    out = dialogues_dir(paths)
    for plan in plan_dialogues(clips, count=count, seconds=seconds, seed=seed):
        wav, ref = out / f"{plan.name}.wav", out / f"{plan.name}.json"
        if wav.is_file() and ref.is_file():
            continue
        reference = render_dialogue(plan, lambda clip: load_mono16k(wavs[clip.file]), wav)
        ref.write_text(json.dumps([asdict(u) for u in reference], ensure_ascii=False), "utf-8")
    return out


def dialogues_dir(paths: BenchPaths) -> Path:
    return paths.data / "speech-gl" / "dialogues"


def run_captions(
    paths: BenchPaths,
    pipeline: Path,
    *,
    transcribe: Callable[..., SpeechTranscript] | None = None,
    limit: int | None = None,
) -> Path:
    """Captions every dialogue with a pipeline's settings and writes results.json and a summary."""
    config: dict[str, Any] = tomllib.loads(pipeline.read_text(encoding="utf-8"))["captions"]
    options = CaptionOptions(
        model=str(config.get("model", "auto")),
        transcribe=functools.partial(
            transcribe or transcribe_speech_in_child, beam_size=int(config.get("beam_size", 5))
        ),
        steps=(speakers_in_child,) if config.get("speakers") else (),
    )
    # Transcripts are kept by settings and code version, so a change to the metrics or the
    # caption rules is measured again in seconds; the time is the one of the first run.
    key = hashlib.sha256(
        json.dumps([config, SPEECH_VERSION, SPEAKERS_VERSION], sort_keys=True).encode()
    ).hexdigest()[:16]
    cache = paths.cache / "captions" / key
    rows: list[dict[str, Any]] = []
    all_onsets: list[float] = []
    said: list[str] = []
    written: list[str] = []
    audio_seconds = elapsed = 0.0
    peak_vram = 0.0
    for wav in sorted(dialogues_dir(paths).glob("*.wav"))[:limit]:
        reference = [
            RefUtterance(**u) for u in json.loads(wav.with_suffix(".json").read_text("utf-8"))
        ]
        cached = cache / f"{wav.stem}.json"
        known = transcript_from(json.loads(cached.read_text("utf-8"))) if cached.is_file() else None
        started = time.monotonic()
        with GpuSampler() as gpu:
            captions, transcript = caption_audio(wav, "gl", options, transcript=known)
        seconds = time.monotonic() - started
        if known is None:
            cache.mkdir(parents=True, exist_ok=True)
            cached.write_text(json.dumps(asdict(transcript), ensure_ascii=False), "utf-8")
            cached.with_suffix(".seconds").write_text(str(seconds))
        else:
            seconds = float(cached.with_suffix(".seconds").read_text())
        metrics = caption_metrics(reference, captions, transcript.words, options.rules, 25.0)
        rows.append({"name": wav.stem, "seconds": round(seconds, 1)} | asdict(metrics))
        all_onsets += metrics.onsets
        said += [u.text for u in reference]
        written += [" ".join(c.lines).replace("-", " ") for c in captions]
        audio_seconds += load_seconds(wav)
        elapsed += seconds
        peak_vram = max(peak_vram, (gpu.peak_mb or 0.0) / 1024)
    speakers = [r["speaker_word_error"] for r in rows if r["speaker_word_error"] is not None]
    errors = [abs(o) for o in all_onsets]
    total = {
        "wer": round(text_errors(" ".join(said), " ".join(written)).wer, 4),
        "speaker_word_error": round(statistics.mean(speakers), 4) if speakers else None,
        "onset_error_median": round(statistics.median(errors), 3) if errors else None,
        "onset_error_p90": round(_percentile(errors, 0.9), 3) if errors else None,
        # Negative: captions come in before the voice.
        "onset_bias": round(statistics.median(all_onsets), 3) if all_onsets else None,
        "onset_missing": sum(r["onset_missing"] for r in rows),
        "captions": sum(r["captions"] for r in rows),
        "violations": {
            k: sum(r["violations"][k] for r in rows)
            for k in (rows[0]["violations"] if rows else {})
        },
        "seconds_per_hour": round(elapsed / audio_seconds * 3600, 1) if audio_seconds else None,
        "peak_vram_gb": round(peak_vram, 2),
        "peak_ram_gb": round(resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss / 2**20, 2),
    }
    name = pipeline.stem
    out = paths.results / f"{datetime.date.today().isoformat()}-{name}"  # noqa: DTZ011 - a folder name
    out.mkdir(parents=True, exist_ok=True)
    results = {"pipeline": name, "config": config, "total": total, "dialogues": rows}
    (out / "results.json").write_text(json.dumps(results, indent=1, ensure_ascii=False), "utf-8")
    (out / "summary.md").write_text(_summary(name, config, total, len(rows)), "utf-8")
    return out


def load_seconds(wav: Path) -> float:
    import wave

    with wave.open(str(wav)) as audio:
        return float(audio.getnframes() / audio.getframerate())


def _violation_keys(rows: Sequence[dict[str, Any]]) -> list[str]:
    return list(rows[0]["violations"]) if rows else []


def _summary(name: str, config: dict[str, Any], total: dict[str, Any], count: int) -> str:
    rows = "\n".join(f"| {key} | {value} |" for key, value in total.items())
    return (
        f"# {name}\n\nInterview captions on {count} Galician dialogues (OpenSLR 77, CC BY-SA "
        f"4.0, read speech joined into interviews).\n\nSettings: `{json.dumps(config)}`\n\n"
        f"| Metric | Value |\n|---|---|\n{rows}\n"
    )


def _speaker_error(reference: Sequence[RefUtterance], words: Sequence[TimedWord]) -> float | None:
    pairs: list[tuple[str, str]] = []
    for word in words:
        if word.speaker is None:
            continue
        middle = (word.start + word.end) / 2
        owner = next((u.speaker for u in reference if u.start - 0.2 <= middle <= u.end + 0.2), None)
        if owner is not None:
            pairs.append((owner, word.speaker))
    if not pairs:
        return None
    labels = sorted({said for said, _ in pairs} | {guessed for _, guessed in pairs})
    if len(labels) > 2:
        labels = labels[:2]
    swap = dict(zip(labels, reversed(labels), strict=True)) if len(labels) == 2 else {}
    straight = sum(said != guessed for said, guessed in pairs)
    crossed = sum(said != swap.get(guessed, guessed) for said, guessed in pairs)
    return round(min(straight, crossed) / len(pairs), 4)


def _percentile(values: Sequence[float], q: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, round(q * (len(ordered) - 1)))]
