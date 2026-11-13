"""Timed words into captions, cut where a subtitler would cut them.

Words gather into a caption while they fit in two lines and seven seconds. A change of speaker,
or a sentence that ends before a pause, always starts a new caption. When the words overflow,
the cut goes to the best place in what was gathered: a sentence end, then a pause, then a comma,
then before a conjunction, and never right after a word that leans on the next one. Finally a
short question and its short answer share one caption, a line each with a dash, as in dialogue.
"""

from collections.abc import Sequence

from karaoke_engine.captions.lines import break_lines, leans_forward
from karaoke_engine.captions.rules import Caption, Rules, TimedWord

_SENTENCE_END = ".?!…"
_CLAUSE_END = ",;:"
_CONJUNCTIONS = frozenset("e ou nin pero mais que se como cando porque pois y".split())  # noqa: SIM905 - a word list reads best as text
# A question and its answer share a caption only if the answer comes this soon after it.
_DIALOGUE_GAP = 1.0
_DASH = "-"


def group_captions(words: Sequence[TimedWord], rules: Rules) -> list[Caption]:
    """Captions over all the words, in order; their times are the words' until timing.py."""
    captions: list[Caption] = []
    for run in _runs(words, rules):
        captions += [_caption(chunk, rules) for chunk in _chunks(run, rules)]
    return _dialogues(captions, rules)


def _runs(words: Sequence[TimedWord], rules: Rules) -> list[list[TimedWord]]:
    """Stretches that never share a caption: split at speaker changes and ended sentences."""
    runs: list[list[TimedWord]] = []
    for word in words:
        if runs:
            last = runs[-1][-1]
            ended = last.text[-1] in _SENTENCE_END and word.start - last.end >= rules.pause_split
            if word.speaker == last.speaker and not ended:
                runs[-1].append(word)
                continue
        runs.append([word])
    return runs


def _chunks(run: list[TimedWord], rules: Rules) -> list[list[TimedWord]]:
    chunks: list[list[TimedWord]] = []
    current: list[TimedWord] = []
    for word in run:
        if not current or _fits([*current, word], rules):
            current.append(word)
            continue
        cut = _best_cut(current, word, rules)
        chunks.append(current[:cut])
        current = [*current[cut:], word]
        # What was carried over plus the new word may still not fit (a very long word).
        while len(current) > 1 and not _fits(current, rules):
            cut = _best_cut(current[:-1], current[-1], rules)
            chunks.append(current[:cut])
            current = current[cut:]
    if current:
        chunks.append(current)
    return chunks


def _fits(words: Sequence[TimedWord], rules: Rules) -> bool:
    if words[-1].end - words[0].start > rules.max_duration:
        return False
    return break_lines([w.text for w in words], rules) is not None


def _best_cut(current: Sequence[TimedWord], following: TimedWord, rules: Rules) -> int:
    """How many words of `current` close the caption: the best boundary, the latest on a tie."""
    best_rank, best_cut = _rank(current[-1], following, rules), len(current)
    for cut in range(len(current) - 1, 0, -1):
        rank = _rank(current[cut - 1], current[cut], rules)
        if rank < best_rank:
            best_rank, best_cut = rank, cut
    return best_cut


def _rank(before: TimedWord, after: TimedWord, rules: Rules) -> int:
    """How good the boundary between two words is to end a caption (lower is better)."""
    if before.text[-1] in _SENTENCE_END:
        return 0
    if after.start - before.end >= rules.pause_split:
        return 1
    if before.text[-1] in _CLAUSE_END:
        return 2
    if leans_forward(before.text):
        return 5
    if after.text.lower() in _CONJUNCTIONS:
        return 3
    return 4


def _caption(words: Sequence[TimedWord], rules: Rules) -> Caption:
    lines = break_lines([w.text for w in words], rules) or (" ".join(w.text for w in words),)
    speaker = words[0].speaker
    return Caption(words[0].start, words[-1].end, lines, (speaker,) * len(lines), tuple(words))


def _dialogues(captions: list[Caption], rules: Rules) -> list[Caption]:
    out: list[Caption] = []
    for caption in captions:
        previous = out[-1] if out else None
        if previous is not None and _is_exchange(previous, caption, rules):
            out[-1] = Caption(
                previous.start,
                caption.end,
                (_DASH + previous.lines[0], _DASH + caption.lines[0]),
                (previous.speakers[0], caption.speakers[0]),
                previous.words + caption.words,
            )
            continue
        out.append(caption)
    return out


def _is_exchange(first: Caption, second: Caption, rules: Rules) -> bool:
    """A short line and a short reply from someone else, close enough to read together."""
    single = len(first.lines) == 1 and len(second.lines) == 1
    if not single or first.speakers[0] == second.speakers[0] or first.lines[0][:1] == _DASH:
        return False
    short = all(len(c.lines[0]) + len(_DASH) <= rules.max_chars for c in (first, second))
    close = second.start - first.end <= _DIALOGUE_GAP
    return short and close and second.end - first.start <= rules.max_duration
