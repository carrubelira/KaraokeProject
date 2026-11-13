"""Where a caption's text breaks into lines, the way a subtitler would break it.

One line when it fits. Otherwise every split that leaves both lines short enough is scored: a
line never ends on a word that leans on the next one ("o | barco"), a break after punctuation
reads best, the lower line may be the longer one (the eye starts at the bottom), and the two
lines should not be too uneven.
"""

from collections.abc import Sequence

from karaoke_engine.captions.rules import FUNCTION_WORDS, Rules

_CLAUSE_END = ".,;:?!…"
_OPENERS = "¿¡«\"'(-"
_DANGLING = 100.0
_AFTER_PUNCTUATION = -20.0
_TOP_LONGER = 5.0
_UNEVEN = 0.25  # per character of difference


def break_lines(words: Sequence[str], rules: Rules) -> tuple[str, ...] | None:
    """The caption's lines, or None when the words do not fit in rules.max_lines lines."""
    whole = " ".join(words)
    if len(whole) <= rules.max_chars and words:
        return (whole,)
    if rules.max_lines < 2:
        return None
    best: tuple[float, tuple[str, str]] | None = None
    for cut in range(1, len(words)):
        top, bottom = " ".join(words[:cut]), " ".join(words[cut:])
        if len(top) > rules.max_chars or len(bottom) > rules.max_chars:
            continue
        score = _score(words[cut - 1], top, bottom)
        if best is None or score < best[0]:
            best = (score, (top, bottom))
    return best[1] if best else None


def leans_forward(word: str) -> bool:
    """True for a word that should not end a line or a caption ("de", "o", "que")."""
    return word.lower().lstrip(_OPENERS) in FUNCTION_WORDS


def _score(last: str, top: str, bottom: str) -> float:
    score = _UNEVEN * abs(len(top) - len(bottom))
    if leans_forward(last):
        score += _DANGLING
    if last[-1] in _CLAUSE_END:
        score += _AFTER_PUNCTUATION
    if len(top) > len(bottom):
        score += _TOP_LONGER
    return score
