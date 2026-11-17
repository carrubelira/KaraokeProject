"""The short list of places worth a second look while watching the interview through.

Someone watches every interview in full before it goes to the museum, so this is a guide, not a
safety net: only strong signals go in (words the model was unsure of, captions too fast to read,
voice with no text, text the guards threw away, unsure speaker changes, and edits that broke the
rules), one line per caption.
The list is read by the owner, in Spanish, with timecodes to jump to in DaVinci Resolve.
"""

from collections.abc import Sequence
from dataclasses import dataclass

from karaoke_engine.captions.lines import leans_forward
from karaoke_engine.captions.rules import Caption, Rules
from karaoke_engine.captions.timing import cps


@dataclass(frozen=True)
class ReviewItem:
    start: float
    text: str
    reasons: tuple[str, ...]


def review_items(
    captions: Sequence[Caption],
    rules: Rules,
    *,
    low_confidence: float,
    missed: Sequence[tuple[float, float]] = (),
    dropped: Sequence[tuple[float, float, str]] = (),
    unsure_speaker: Sequence[float] = (),
) -> list[ReviewItem]:
    items: list[ReviewItem] = []
    previous_end = float("-inf")
    for caption in captions:
        reasons: list[str] = []
        longest = max((len(line) for line in caption.lines), default=0)
        if longest > rules.max_chars:
            reasons.append(f"línea de {longest} caracteres")
        if len(caption.lines) > rules.max_lines:
            reasons.append(f"{len(caption.lines)} líneas")
        if caption.start < previous_end:
            reasons.append("se solapa con el anterior")
        previous_end = caption.end
        unsure = [
            w.text
            for w in caption.words
            if w.confidence < low_confidence and _says_something(w.text)
        ]
        if unsure:
            reasons.append("palabra dudosa: " + ", ".join(f"«{w}»" for w in unsure))
        speed = cps(caption)
        if speed > rules.review_cps:
            reasons.append(f"lectura rápida: {speed:.0f} car./s")
        if any(caption.start <= t <= caption.end for t in unsure_speaker):
            reasons.append("¿quién habla?")
        if reasons:
            items.append(ReviewItem(caption.start, " / ".join(caption.lines), tuple(reasons)))
    items += [
        ReviewItem(start, "", (f"voz sin texto ({end - start:.1f} s)",)) for start, end in missed
    ]
    items += [ReviewItem(start, text, ("texto descartado",)) for start, _, text in dropped]
    return sorted(items, key=lambda item: item.start)


def _says_something(word: str) -> bool:
    """Not a short or grammatical word: Whisper is always unsure of a segment's first "Que"."""
    letters = "".join(ch for ch in word if ch.isalnum())
    return len(letters) > 2 and not leans_forward(word)


def timecode(seconds: float, fps: float) -> str:
    """HH:MM:SS:FF as an editor's timeline starting at 00:00:00:00 shows it (non-drop)."""
    base = round(fps)
    frames = round(seconds * fps)
    total, frame = divmod(frames, base)
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}:{frame:02d}"


def format_review(
    items: Sequence[ReviewItem],
    *,
    video: str,
    captions: int,
    fps: float,
    elapsed: float,
    fast: int = 0,
    max_cps: float = 17.0,
) -> str:
    minutes, secs = divmod(round(elapsed), 60)
    head = [
        f"Revisión de subtítulos · {video}",
        f"{captions} subtítulos · {len(items)} para mirar · hecho en {minutes} min {secs} s",
        f"Tiempos a {fps:g} fps. En DaVinci, la línea de tiempo debe empezar en 00:00:00:00.",
    ]
    if fast:
        head.append(
            f"{fast} pasan de {max_cps:g} car./s: el habla es rápida y se dejan literales; "
            "aquí solo salen los que no se pueden leer."
        )
    head += [
        "",
    ]
    lines = [
        f"{timecode(item.start, fps)}  ({item.start:.1f} s)  {'; '.join(item.reasons)}"
        + (f"  «{item.text}»" if item.text else "")
        for item in items
    ]
    return "\n".join(head + lines) + "\n"
