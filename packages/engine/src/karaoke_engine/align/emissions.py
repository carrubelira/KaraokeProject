"""CTC emissions of the vocals: per-frame log-probabilities of the letters the lyrics use.

Only the columns the lyrics need leave the GPU (plus the blank and the best other letter), so a
model with ten thousand symbols costs no more memory than one with forty.
"""

import contextlib
import json
import shutil
import subprocess
import sys
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt

from karaoke_engine.align.audio import SAMPLE_RATE
from karaoke_engine.align.ctc import ANY, BLANK
from karaoke_engine.align.models import CtcModelSpec

_DELIMITERS = ("|", " ")
CACHE = Path.home() / ".cache" / "karaoke" / "models" / "ctc"


@dataclass(frozen=True)
class Vocab:
    ids: dict[str, int]
    blank: int
    delimiter: int | None
    upper: bool
    fallbacks: dict[str, str]

    @classmethod
    def from_mapping(
        cls, mapping: dict[str, int], blank: int, fallbacks: dict[str, str]
    ) -> "Vocab":
        letters = [token for token in mapping if len(token) == 1 and token.isalpha()]
        delimiter = next((mapping[d] for d in _DELIMITERS if d in mapping), None)
        upper = bool(letters) and not any(token.islower() for token in letters)
        return cls(dict(mapping), blank, delimiter, upper, dict(fallbacks))

    def encode(self, word: str) -> tuple[int, ...]:
        """Ids of a word's letters: the letter, its fallback, its base letter, or nothing."""
        ids = []
        for ch in word:
            token = self.token(ch)
            if token is not None:
                ids.append(token)
        return tuple(ids)

    def token(self, ch: str) -> int | None:
        """The id of one letter, or None when the model has nothing close to it."""
        for candidate in (ch, self.fallbacks.get(ch.lower(), ""), _base(ch)):
            if not candidate:
                continue
            cased = candidate.upper() if self.upper else candidate.lower()
            if cased in self.ids and self.ids[cased] not in (self.blank, self.delimiter):
                return self.ids[cased]
        return None


@dataclass(frozen=True)
class Emissions:
    log_probs: npt.NDArray[np.float32]  # (frames, 2 + ids): blank, best other, then the ids
    frame_seconds: float


def compact(
    log_probs: npt.NDArray[np.floating], blank: int, ids: Sequence[int]
) -> npt.NDArray[np.float32]:
    """Blank, best non-blank and the requested columns, in the layout align_segments reads."""
    others = log_probs.copy()
    others[:, blank] = -np.inf
    out = np.empty((log_probs.shape[0], 2 + len(ids)), dtype=np.float32)
    out[:, BLANK] = log_probs[:, blank]
    out[:, ANY] = others.max(axis=1)
    out[:, 2:] = log_probs[:, list(ids)]
    return out


def blend(
    members: Sequence[Emissions],
    columns: Sequence[Sequence[int | None]],
    weights: Sequence[float],
) -> Emissions:
    """The weighted mean of several models' probabilities, on the first one's frames.

    Two models trained on different sound (speech of one language, music of many) miss
    different passages: a letter either of them hears is heard. The mean is of the
    probabilities, not of their logarithms: a CTC model puts each letter on a frame or two and
    two models rarely pick the same one, so a mean of logarithms would make every letter
    unlikely everywhere. `columns[m][k]` is where member m keeps letter k (None when it does not
    know the letter: the others decide it alone). Members with another frame rate are read at
    the nearest frame.
    """
    first = members[0]
    frames = first.log_probs.shape[0]
    width = 2 + len(columns[0])
    out = np.full((frames, width), -np.inf, dtype=np.float64)
    shared = np.zeros(width, dtype=np.float64)
    for member, places, weight in zip(members, columns, weights, strict=True):
        if weight <= 0 or not len(member.log_probs):
            continue
        ratio = first.frame_seconds / member.frame_seconds
        rows = np.minimum((np.arange(frames) * ratio + 0.5).astype(int), len(member.log_probs) - 1)
        source = [BLANK, ANY, *(place for place in places if place is not None)]
        target = [BLANK, ANY, *(2 + k for k, place in enumerate(places) if place is not None)]
        heard = member.log_probs[rows][:, source].astype(np.float64) + np.log(weight)
        out[:, target] = np.logaddexp(out[:, target], heard)
        shared[target] += weight
    known = shared > 0
    out[:, known] -= np.log(shared[known])
    return Emissions(out.astype(np.float32), first.frame_seconds)


def compact_tensor(log_probs: Any, blank: int, ids: Sequence[int]) -> npt.NDArray[np.float32]:
    """compact() on a torch tensor, so only the needed columns leave the GPU."""
    import torch

    others = log_probs.clone()
    others[:, blank] = -torch.inf
    columns = [log_probs[:, blank : blank + 1], others.max(dim=1, keepdim=True).values]
    if ids:
        columns.append(log_probs[:, list(ids)])
    out: npt.NDArray[np.float32] = torch.cat(columns, dim=1).float().cpu().numpy()
    return out


class EmissionModel:
    def __init__(
        self,
        spec: CtcModelSpec,
        device: str = "cuda",
        dtype: str = "float16",
        window_seconds: float = 30.0,
        context_seconds: float = 2.0,
    ) -> None:
        self.spec = spec
        self.device = device
        self.dtype = dtype
        self.window_seconds = window_seconds
        self.context_seconds = context_seconds
        self._net: Any = None
        self._features: Any = None
        self._vocab: Vocab | None = None

    @property
    def vocab(self) -> Vocab:
        """The model's letters, read from its two small files: the weights are not needed."""
        if self._vocab is None:
            repo, revision = self.spec.repo, self.spec.revision
            mapping = _read_json(_hub_file(repo, "vocab.json", revision))
            blank = _read_json(_hub_file(repo, "config.json", revision))["pad_token_id"]
            self._vocab = Vocab.from_mapping(mapping, blank, self.spec.fallbacks)
        return self._vocab

    def load(self) -> None:
        import torch
        from transformers import AutoFeatureExtractor, AutoModelForCTC

        half = self.device != "cpu" and self.dtype == "float16"
        source, revision = source_of(self.spec, half)
        # Untyped in transformers, missing without the ml extra: Any either way.
        extractor: Any = AutoFeatureExtractor
        self._features = extractor.from_pretrained(source, revision=revision)
        net = AutoModelForCTC.from_pretrained(
            source, revision=revision, dtype=torch.float16 if half else torch.float32
        )
        self._net = net.to(self.device).eval()

    def emissions(self, samples: npt.NDArray[np.float32], ids: Sequence[int]) -> Emissions:
        """Compact emissions computed window by window, with context on both sides."""
        import torch

        if self._net is None:
            self.load()
        blank = self.vocab.blank
        window = round(self.window_seconds * SAMPLE_RATE)
        context = round(self.context_seconds * SAMPLE_RATE)
        parts = []
        for start in range(0, len(samples), window):
            stop = min(start + window, len(samples))
            left, right = max(0, start - context), min(len(samples), stop + context)
            inputs = self._features(
                samples[left:right], sampling_rate=SAMPLE_RATE, return_tensors="pt"
            )
            inputs = {
                key: value.to(self.device, dtype=self._net.dtype)
                if value.is_floating_point()
                else value.to(self.device)
                for key, value in inputs.items()
            }
            with torch.inference_mode():
                logits = self._net(**inputs).logits[0].float()
            per_sample = logits.shape[0] / (right - left)
            first = round((start - left) * per_sample)
            last = round((stop - left) * per_sample)
            parts.append(compact_tensor(logits[first:last].log_softmax(dim=-1), blank, ids))
        log_probs = np.concatenate(parts) if parts else np.zeros((0, 2 + len(ids)), np.float32)
        frame_seconds = len(samples) / SAMPLE_RATE / max(log_probs.shape[0], 1)
        return Emissions(log_probs, frame_seconds)

    def unload(self) -> None:
        """Frees the model, on the GPU and in RAM, before another one loads."""
        import gc

        self._net = None
        self._features = None
        gc.collect()
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass
        _give_memory_back()


def source_of(spec: CtcModelSpec, half: bool) -> tuple[str, str | None]:
    """Where a model loads from: its repository at its revision, or its 16-bit copy."""
    if half and spec.half:
        return str(half_copy(spec)), None
    return spec.repo, spec.revision


def half_copy(spec: CtcModelSpec) -> Path:
    """The model stored in 16 bits in the model cache, made once in a process of its own.

    A 600-million-parameter checkpoint published in 32 bits is 2.3 GB to read, for a model that
    runs in 16 bits: the copy loads in half the memory and half the time. Making it holds both
    at once, so it runs alone, and it only takes its final name when it is complete.
    """
    target = CACHE / f"{spec.repo.replace('/', '--')}-{spec.revision[:12]}-fp16"
    if (target / "model.safetensors").is_file():
        return target
    print(f"First use of {spec.repo}: storing it in 16 bits once.", file=sys.stderr)  # noqa: T201 - a wait the user should know about
    side = target.with_name(target.name + ".partial")
    shutil.rmtree(side, ignore_errors=True)
    command = [sys.executable, "-m", "karaoke_engine.align.emissions", spec.repo, spec.revision]
    try:
        subprocess.run([*command, str(side)], check=True)
    except subprocess.CalledProcessError as exc:
        shutil.rmtree(side, ignore_errors=True)
        raise RuntimeError(
            f"could not store {spec.repo} in 16 bits (exit code {exc.returncode})"
        ) from exc
    shutil.rmtree(target, ignore_errors=True)  # a copy left without its weights
    side.replace(target)
    return target


def _halve(repo: str, revision: str, target: Path) -> None:
    import torch
    from transformers import AutoFeatureExtractor, AutoModelForCTC

    extractor: Any = AutoFeatureExtractor
    net = AutoModelForCTC.from_pretrained(repo, revision=revision, dtype=torch.float16)
    net.save_pretrained(target)
    extractor.from_pretrained(repo, revision=revision).save_pretrained(target)


def _hub_file(repo: str, name: str, revision: str) -> str:
    from huggingface_hub import hf_hub_download

    return str(hf_hub_download(repo, name, revision=revision))


def _read_json(path: str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _give_memory_back() -> None:
    """Returns freed heap to the system (glibc keeps it otherwise), so models do not pile up."""
    import ctypes
    import ctypes.util

    name = ctypes.util.find_library("c")
    if name:
        with contextlib.suppress(OSError, AttributeError):
            ctypes.CDLL(name).malloc_trim(0)


def _base(ch: str) -> str:
    base = "".join(c for c in unicodedata.normalize("NFD", ch) if not unicodedata.combining(c))
    return base if len(base) == 1 else ""


if __name__ == "__main__":
    _halve(sys.argv[1], sys.argv[2], Path(sys.argv[3]))
