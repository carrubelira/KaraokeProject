"""The lyrics aligner: pasted lyrics and separated vocals in, timed lines and words out.

It reads the lyrics the way a lyrics site writes them (parse_lyrics), turns each word into the
letters a singer says (spoken), and lets the CTC path rest between lines, skip lines nobody
sings, sing a stanza's lines again where the site wrote them once, and keep letters out of the
instrumental breaks (align_segments). A repeat mark that may cover more than its line ("(x4)"
after a couplet) is read the way the audio fits best. After the path, word ends are kept out of
silence.
"""

import itertools
import math
import unicodedata
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import numpy as np
import numpy.typing as npt

from karaoke_contracts import Line, Part, Word
from karaoke_engine.align.activity import vocal_activity
from karaoke_engine.align.audio import SAMPLE_RATE, load_mono16k
from karaoke_engine.align.ctc import BestPath, Segment, align_segments, best_path
from karaoke_engine.align.emissions import EmissionModel, Emissions, Vocab, blend, half_copy
from karaoke_engine.align.lyrics import LyricLine, parse_lyrics, repeat_marks, singer_id
from karaoke_engine.align.models import (
    DEFAULT_BY_LANGUAGE,
    DEFAULT_SECOND,
    FALLBACK_MODEL,
    MODELS,
    WIDE_FALLBACK_MODEL,
)
from karaoke_engine.align.spoken import spoken
from karaoke_engine.align.syllables import syllables

_HOP = 0.02
# A line start moves back to the voice onset only if the voice was silent this long before it,
# and the onset is at most this far back.
_ONSET_SILENCE = 0.2
_ONSET_REACH = 0.5
_END_SLACK = 0.1
_END_GAP = 0.3
# A backing part may start this long before the lead line it answers.
_BACKING_MARGIN = 0.5
# A repeat mark covers more than its line only if that reading's path scores this much better,
# and no more than this many readings are tried in one song (each is a path search).
_READING_MARGIN = 1.0
_MAX_READINGS = 24
# A language without a model of its own gets the music model when it can write at least this
# share of the letters of the lyrics (a stray word in another script does not count).
_FALLBACK_COVERAGE = 0.9


class _Model(Protocol):
    @property
    def vocab(self) -> Vocab: ...

    def load(self) -> None: ...

    def emissions(self, samples: npt.NDArray[np.float32], ids: Sequence[int]) -> Emissions: ...

    def unload(self) -> None: ...


# A letter as each model in use knows it: one id per model, None where a model has none.
_Key = tuple[int | None, ...]


@dataclass(frozen=True)
class _Tokens:
    ids: tuple[_Key, ...]  # the letters of a line, with delimiters between words
    owner: tuple[int, ...]  # word index per token, -1 for delimiters


class LyricsAligner:
    name = "lyrics-ctc"
    # Bumped when a default changes too: defaults are not part of the bench cache key.
    version = "16"  # a second model trained on songs (the first decides repeats), resting costs

    # Defaults measured on the quick, stress, private and jamendo sets (decisions 005 and 019).
    # Skip costs are per letter: a flat cost per line rewarded cramming many short lines into the
    # audio. Cheap skips at the edges help clips but can drop a whole sung verse, so they are
    # off. Moving line starts to the voice onset made JamendoLyrics worse (its starts follow the
    # vowel). The music model weighs 0.3 next to a language's own: at 0.5 word ends come later,
    # at 0.7 English gets worse. Resting costs 0.05 per silent frame: enough to keep a one-letter
    # word out of an instrumental break, and from 0.2 on it moves words across real pauses.
    def __init__(
        self,
        model: str | None = None,
        second: str | None = None,
        second_weight: float = 0.3,
        filler_penalty: float = 3.0,
        skip_penalty: float = 6.0,
        backing_skip_penalty: float = 4.0,
        overlap_backing: bool = False,
        overlap_absent_penalty: float = 6.0,
        backing_min_confidence: float = 0.05,
        edge_skip_penalty: float = math.inf,
        silence_penalty: float = 4.0,
        rest_penalty: float = 0.05,
        repeat_penalty: float = 30.0,
        refine_onsets: bool = False,
        parts: bool = True,
        char_map: dict[str, str] | None = None,
        device: str = "cuda",
        dtype: str = "float16",
        emission_model: Any = None,
        second_emission_model: Any = None,
    ) -> None:
        if not 0.0 <= second_weight <= 1.0:
            raise ValueError("second_weight is the second model's share, from 0 to 1")
        self.model = model
        # A second model whose emissions are averaged with the first one's (see emissions.blend).
        # None is the default one, which only joins a language's default model: a model chosen
        # by hand works alone. An empty name turns it off.
        self.second = second
        self.second_weight = second_weight
        self.filler_penalty = filler_penalty
        self.skip_penalty = skip_penalty
        self.backing_skip_penalty = backing_skip_penalty
        self.overlap_backing = overlap_backing
        self.overlap_absent_penalty = overlap_absent_penalty
        self.backing_min_confidence = backing_min_confidence
        self.edge_skip_penalty = edge_skip_penalty
        self.silence_penalty = silence_penalty
        self.rest_penalty = rest_penalty
        self.repeat_penalty = repeat_penalty
        self.refine_onsets = refine_onsets
        self.parts = parts
        self.char_map = char_map or {}
        self.device = device
        self.dtype = dtype
        self._injected: list[_Model] | None = [
            m for m in (emission_model, second_emission_model) if m is not None
        ] or None
        self._loaded: tuple[tuple[str, ...], list[_Model]] | None = None
        # The models each language's last song was aligned with (for provenance).
        self._used: dict[str, tuple[str, ...]] = {}

    def load(self) -> None:
        """Loads the chosen model ahead of time; without one, it waits to know the language."""
        if self._injected is None and self.model is not None:
            self._models_for("")

    def align(self, vocals: Path, lyrics_lines: Sequence[str], language: str) -> list[Line]:
        return self.align_text(vocals, "\n".join(lyrics_lines), language)

    def align_text(self, vocals: Path, lyrics: str, language: str) -> list[Line]:
        lines = parse_lyrics(lyrics)
        models = self._models_for(language, lines)
        vocabs = [model.vocab for model in models]
        known: dict[tuple[str, ...], _Tokens] = {}

        def tokens_of(line: LyricLine) -> _Tokens:
            if line.words not in known:
                known[line.words] = self._tokens(line, vocabs, language)
            return known[line.words]

        # Every reading of the repeat marks repeats these same lines: one set of columns.
        tokens = [tokens_of(line) for line in lines]
        used = sorted(
            {token for line in tokens for token in line.ids},
            key=lambda key: tuple(-1 if part is None else part for part in key),
        )
        column = {token: i + 2 for i, token in enumerate(used)}

        samples = load_mono16k(vocals)
        # With two models, the first one alone (`judge`) decides the song's shape: how each
        # repeat mark reads and which lines are sung again. The second model's probabilities are
        # spread over time, and in the mean of the two a line stretched over a repeat costs less
        # than singing it again (decision 019). Both decide where every word goes.
        emissions, judge = self._emissions(models, samples, used)
        active = vocal_activity(samples, SAMPLE_RATE, _HOP)
        frame_active = _resample(active, emissions.log_probs.shape[0], emissions.frame_seconds)
        penalty = np.where(frame_active, 0.0, self.silence_penalty).astype(np.float32)

        def search(lines: list[LyricLine]) -> tuple[list[int], BestPath]:
            order = [i for i in range(len(lines)) if tokens_of(lines[i]).ids]
            segments = [self._segment(lines[i], tokens_of(lines[i]), column) for i in order]
            found = best_path(judge.log_probs, segments, self.filler_penalty, penalty,
                              self.repeat_penalty, self.rest_penalty)  # fmt: skip
            return order, found

        scopes = self._read_marks(
            lyrics, lambda reading: search(parse_lyrics(lyrics, reading))[1].score
        )
        if scopes:
            lines = parse_lyrics(lyrics, scopes)
            tokens = [tokens_of(line) for line in lines]

        # One path through every line, backing parts in their written place (mostly echoes and
        # answers right after the lead). With overlap_backing, a backing part that does not fit
        # there gets a second chance alone, over its lead line; off by default, because on the
        # public songs it placed more words wrong than right (decision 006).
        order, found = search(lines)
        segments = {i: self._segment(lines[i], tokens[i], column) for i in order}
        paths = dict(zip(order, found.paths, strict=True))
        placed = {i: path.spans for i, path in paths.items() if path.spans is not None}
        again = [(i, spans) for i, path in paths.items() for spans in path.repeats]
        if judge is not emissions:
            sung = _sung_order(order, found)
            timed = best_path(emissions.log_probs, [segments[i] for i in sung],
                             self.filler_penalty, penalty, math.inf, self.rest_penalty)  # fmt: skip
            placed, again = {}, []
            for i, visit in zip(sung, timed.paths, strict=True):
                if visit.spans is None:
                    continue
                if i in placed:
                    again.append((i, visit.spans))
                else:
                    placed[i] = visit.spans
        first_pass = set(placed)
        leads = [i for i in order if not lines[i].backing]
        skipped = [i for i in order if lines[i].backing and i not in placed]
        for i in skipped if self.overlap_backing else []:
            first, last = _backing_window(i, leads, placed, len(emissions.log_probs),
                                          emissions.frame_seconds)  # fmt: skip
            cost = self.overlap_absent_penalty * len(tokens[i].ids)
            alone = Segment(segments[i].tokens, segments[i].owner, cost, cost)
            [path] = align_segments(
                emissions.log_probs[first:last], [alone], self.filler_penalty, penalty[first:last]
            )
            if path.spans is not None:
                placed[i] = [(a + first, b + first) for a, b in path.spans]

        out: list[Line] = []
        for i, spans in [*placed.items(), *again]:
            words = self._words(lines[i], tokens[i], spans, emissions, column, active, language)
            overlapped = lines[i].backing and i not in first_pass
            if overlapped and _mean_confidence(words) < self.backing_min_confidence:
                continue  # placed over the lead voice by chance, not sung
            singer = lines[i].singer
            out.append(
                Line(
                    id="l",
                    start=words[0].start,
                    end=max(word.end for word in words),
                    singer=singer_id(singer) if singer else None,
                    role="backing" if lines[i].backing else "lead",
                    words=words,
                )
            )
        out.sort(key=lambda line: line.start)
        return [line.model_copy(update={"id": f"l{k + 1}"}) for k, line in enumerate(out)]

    def _read_marks(self, lyrics: str, score: Callable[[dict[int, int]], float]) -> dict[int, int]:
        """How many lines each repeat mark covers ("(x4)" after a couplet): for each mark that
        could cover more than its line, in order, the reading whose path scores best."""
        marks = repeat_marks(lyrics)
        if not any(most > 1 for most in marks):
            return {}
        scopes: dict[int, int] = {}
        best = score(scopes)
        tries = 1
        for mark, most in enumerate(marks):
            for option in sorted({2, 3, 4, most} & set(range(2, most + 1))):
                if tries >= _MAX_READINGS:
                    return scopes
                trial = {**scopes, mark: option}
                tried = score(trial)
                tries += 1
                if tried > best + _READING_MARGIN:
                    best, scopes = tried, trial
        return scopes

    def _emissions(
        self, models: Sequence[_Model], samples: npt.NDArray[np.float32], used: Sequence[_Key]
    ) -> tuple[Emissions, Emissions]:
        """The letters' log-probabilities: one model's, or the blend of the two together with
        the first one's alone in the same columns (letters it does not know come from the blend).
        """
        members, columns = [], []
        for index, model in enumerate(models):
            ids = sorted({part for key in used if (part := key[index]) is not None})
            place = {token: 2 + k for k, token in enumerate(ids)}
            members.append(model.emissions(samples, ids))
            columns.append([place.get(part) if (part := key[index]) is not None else None
                            for key in used])  # fmt: skip
            if len(models) > 1:
                # One model on the card at a time: each leaves before the other loads.
                model.unload()
        if len(members) == 1:
            return members[0], members[0]
        both = blend(members, columns, [1.0 - self.second_weight, self.second_weight])
        first = blend(members, columns, [1.0, 0.0])
        unknown = np.isneginf(first.log_probs).all(axis=0)
        first.log_probs[:, unknown] = both.log_probs[:, unknown]
        return both, first

    def _segment(self, line: LyricLine, tokens: _Tokens, column: dict[_Key, int]) -> Segment:
        count = len(tokens.ids)
        rate = self.backing_skip_penalty if line.backing else self.skip_penalty
        return Segment(
            tokens=tuple(column[t] for t in tokens.ids),
            owner=tokens.owner,
            skip_penalty=rate * count,
            edge_skip_penalty=min(rate, self.edge_skip_penalty) * count,
            group=line.stanza,
        )

    def _tokens(self, line: LyricLine, vocabs: Sequence[Vocab], language: str) -> _Tokens:
        ids: list[_Key] = []
        owner: list[int] = []
        delimiter = tuple(vocab.delimiter for vocab in vocabs)
        for index, word in enumerate(line.words):
            said = "".join(self.char_map.get(ch, ch) for ch in spoken(word, language))
            for piece in said.split():
                encoded = [key for ch in piece for key in _spell(vocabs, ch)]
                if not encoded:
                    continue
                if ids and any(part is not None for part in delimiter):
                    ids.append(delimiter)
                    owner.append(-1)
                ids += encoded
                owner += [index] * len(encoded)
        return _Tokens(tuple(ids), tuple(owner))

    def _words(
        self,
        line: LyricLine,
        tokens: _Tokens,
        spans: Sequence[tuple[int, int]],
        emissions: Emissions,
        column: dict[_Key, int],
        active: npt.NDArray[np.bool_],
        language: str,
    ) -> list[Word]:
        seconds = emissions.frame_seconds
        lp = emissions.log_probs
        found: list[tuple[float, float, float] | None] = [None] * len(line.words)
        letter_starts: list[list[float]] = [[] for _ in line.words]
        for word in range(len(line.words)):
            mine = [k for k, owner in enumerate(tokens.owner) if owner == word]
            if not mine:
                continue
            letter_starts[word] = [spans[k][0] * seconds for k in mine]
            first, last = spans[mine[0]][0], spans[mine[-1]][1]
            total = sum(
                float(lp[spans[k][0] : spans[k][1] + 1, column[tokens.ids[k]]].sum()) for k in mine
            )
            count = sum(spans[k][1] - spans[k][0] + 1 for k in mine)
            found[word] = (first * seconds, (last + 1) * seconds, math.exp(total / count))
        times = _fill_gaps(found)
        words: list[Word] = []
        for text, (found_start, found_end, confidence) in zip(line.words, times, strict=True):
            start = found_start
            end = _trim_end(found_start, found_end, active)
            if self.refine_onsets and confidence > 0:
                previous_end = words[-1].end if words else 0.0
                start = max(_voice_onset(start, active), min(start, previous_end))
            end = max(end, start)
            parts = self._parts(text, letter_starts[len(words)], start, end, language)
            words.append(
                Word(text=text, start=round(start, 3), end=round(end, 3),
                     confidence=round(confidence, 3), parts=parts)
            )  # fmt: skip
        return words

    def _parts(
        self, text: str, letter_starts: Sequence[float], start: float, end: float, language: str
    ) -> list[Part]:
        """Syllables timed by their first letter, when each letter has its own token."""
        if not self.parts:
            return []
        pieces = syllables(text, language)
        if pieces is None or len(letter_starts) != sum(ch.isalpha() for ch in text):
            return []
        bounds = [start]
        letters = 0
        for piece in pieces[:-1]:
            letters += sum(ch.isalpha() for ch in piece)
            bounds.append(min(max(letter_starts[letters], bounds[-1]), end))
        bounds.append(end)
        return [
            Part(text=piece, start=round(a, 3), end=round(b, 3))
            for piece, (a, b) in zip(pieces, itertools.pairwise(bounds), strict=True)
        ]

    def model_for_language(self, language: str) -> str:
        """The models this aligner uses for a language, as repo@revision (for provenance)."""
        names = self._used.get(language) or self._names_for(language)
        return " + ".join(f"{MODELS[n].repo}@{MODELS[n].revision[:12]}" for n in names)

    def prepare_for(self, language: str) -> None:
        """Stores the big models a language will use in 16 bits, before anything else loads:
        making the copy holds the model twice (emissions.half_copy)."""
        if self._injected is not None or self.device == "cpu" or self.dtype != "float16":
            return
        for name in self.model_names(language):
            if MODELS[name].half:
                half_copy(MODELS[name])

    def model_names(self, language: str) -> tuple[str, ...]:
        """The models a song in this language is aligned with, before its lyrics are known."""
        return self._names_for(language)

    def fallback_for(self, language: str) -> str | None:
        """The model that stood in for a language without one of its own, or None."""
        if self.model is not None or language in DEFAULT_BY_LANGUAGE:
            return None
        return (self._used.get(language) or self._names_for(language))[0]

    def unload(self) -> None:
        """Frees the loaded models, so the next step has the GPU and the memory."""
        if self._loaded is not None:
            for model in self._loaded[1]:
                model.unload()
            self._loaded = None

    def _names_for(self, language: str, lines: Sequence[LyricLine] = ()) -> tuple[str, ...]:
        """The language's model and, when it is another one, the second model."""
        first = self.model or DEFAULT_BY_LANGUAGE.get(language) or _fallback(lines, language)
        second = self.second
        if second is None and self.model is None:
            second = DEFAULT_SECOND
        if not second or second == first or self.second_weight <= 0:
            return (first,)
        return (first, second)

    def _models_for(self, language: str, lines: Sequence[LyricLine] = ()) -> list[_Model]:
        if self._injected is not None:
            return self._injected
        names = self._names_for(language, lines)
        self._used[language] = names
        if self._loaded is not None and self._loaded[0] == names:
            return self._loaded[1]
        self.unload()
        models: list[_Model] = [
            EmissionModel(MODELS[name], device=self.device, dtype=self.dtype) for name in names
        ]
        if len(models) == 1:
            # A single model loads now and stays for the next song; two load when their turn
            # comes (_emissions).
            models[0].load()
        self._loaded = (names, models)
        return models


def _spell(vocabs: Sequence[Vocab], ch: str) -> list[_Key]:
    """A letter as each model knows it (kept when any of them does). A letter none of them has
    is tried as its parts: a Korean syllable block as the letters it is made of."""
    key = tuple(vocab.token(ch) for vocab in vocabs)
    if any(part is not None for part in key):
        return [key]
    parts = unicodedata.normalize("NFD", ch)
    if len(parts) < 2:
        return []
    keys = [tuple(vocab.token(part) for vocab in vocabs) for part in parts]
    return [key for key in keys if any(part is not None for part in key)]


def _fallback(lines: Sequence[LyricLine], language: str) -> str:
    """The model for a language without one of its own: the music model if it can write the
    lyrics, and otherwise the one that knows more scripts."""
    letters = [
        ch for line in lines for word in line.words for ch in spoken(word, language) if ch.isalpha()
    ]
    if not letters:
        return FALLBACK_MODEL
    vocab = _vocab_of(FALLBACK_MODEL)
    known = sum(1 for ch in letters if _spell([vocab], ch))
    return FALLBACK_MODEL if known >= _FALLBACK_COVERAGE * len(letters) else WIDE_FALLBACK_MODEL


def _vocab_of(name: str) -> Vocab:
    return EmissionModel(MODELS[name]).vocab


def heard(lines: Sequence[Line], least: float) -> list[Line]:
    """The lines whose words the aligner could hear where it placed them.

    For lyrics a transcriber wrote: the aligner is a second listener, with another model, and a
    line it gives next to no confidence (the geometric mean of its words') was made up. Lines
    without a rating (numbers, symbols, an aligner that gives none) are kept.
    """
    return [
        line
        for line in lines
        if not any(word.confidence for word in line.words) or _mean_confidence(line.words) >= least
    ]


def _sung_order(order: Sequence[int], found: BestPath) -> list[int]:
    """The lines in the order a path sings them, each time it sings them; a line it left out
    stays in its written place, right after the line before it, so the next search may still
    find it."""
    visits = sorted(
        (spans[0][0], i)
        for i, path in zip(order, found.paths, strict=True)
        for spans in ([path.spans] if path.spans is not None else []) + list(path.repeats)
    )
    left_out = [i for i, path in zip(order, found.paths, strict=True) if path.spans is None]
    sung = [i for i in left_out if not any(j < i for _, j in visits)]
    seen: set[int] = set()
    for _, i in visits:
        sung.append(i)
        if i in seen:
            continue
        seen.add(i)
        later = [j for _, j in visits if j > i]
        sung += [j for j in left_out if i < j < min(later, default=math.inf)]
    return sung


def _mean_confidence(words: Sequence[Word]) -> float:
    rated = [w.confidence for w in words if w.confidence]
    return math.exp(sum(math.log(c) for c in rated) / len(rated)) if rated else 0.0


def _backing_window(
    index: int,
    leads: Sequence[int],
    placed: dict[int, list[tuple[int, int]]],
    frames: int,
    frame_seconds: float,
) -> tuple[int, int]:
    """Frames from just before the lead line before a backing part to the second one after it."""
    before = [i for i in leads if i < index and i in placed]
    after = [i for i in leads if i > index and i in placed]
    margin = round(_BACKING_MARGIN / frame_seconds)
    first = max(placed[before[-1]][0][0] - margin, 0) if before else 0
    last = placed[after[1]][0][0] if len(after) > 1 else frames
    return first, max(last, first)


def _fill_gaps(
    found: Sequence[tuple[float, float, float] | None],
) -> list[tuple[float, float, float]]:
    """Words the model could not spell sit at their neighbour's edge, with confidence 0."""
    out: list[tuple[float, float, float]] = []
    for i, item in enumerate(found):
        if item is not None:
            out.append(item)
            continue
        later = (f[0] for f in found[i + 1 :] if f is not None)
        point = out[-1][1] if out else next(later, 0.0)
        out.append((point, point, 0.0))
    return out


def _resample(active: npt.NDArray[np.bool_], frames: int, seconds: float) -> npt.NDArray[np.bool_]:
    """Activity at the model's frame rate (nearest activity frame for each model frame)."""
    if not len(active):
        return np.zeros(frames, dtype=bool)
    index = np.minimum((np.arange(frames) * seconds / _HOP).astype(int), len(active) - 1)
    resampled: npt.NDArray[np.bool_] = active[index]
    return resampled


def _voice_onset(start: float, active: npt.NDArray[np.bool_]) -> float:
    """Where the voice run holding `start` begins, if it follows a silence and is close."""
    index = min(round(start / _HOP), len(active) - 1)
    if index < 0 or not active[index]:
        return start
    onset = index
    while onset > 0 and active[onset - 1]:
        onset -= 1
    silence = round(_ONSET_SILENCE / _HOP)
    if onset < silence or active[onset - silence : onset].any():
        return start
    return onset * _HOP if start - onset * _HOP <= _ONSET_REACH else start


def _trim_end(start: float, end: float, active: npt.NDArray[np.bool_]) -> float:
    """Ends a word where its voice stops: at the first pause longer than _END_GAP after it starts.

    The release after the voice stops keeps a little of the fade.
    """
    first = min(round(start / _HOP), len(active))
    last = min(round(end / _HOP), len(active))
    gap = round(_END_GAP / _HOP)
    voiced_end = None
    silent = 0
    for frame in range(first, last):
        if active[frame]:
            voiced_end = frame + 1
            silent = 0
            continue
        silent += 1
        if voiced_end is not None and silent > gap:
            break
    if voiced_end is None:
        return end
    return min(end, voiced_end * _HOP + _END_SLACK)
