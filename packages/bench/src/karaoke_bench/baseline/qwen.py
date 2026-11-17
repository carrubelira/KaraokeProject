"""Candidate transcriber: Qwen3-ASR, an audio language model trained on speech, singing and songs.

It knows thirty languages and Galician is not one of them, so it is here to measure the others
against Whisper. Each stretch of singing goes to it on its own, with the language given: a
model that guesses the language must never change the one the user chose.
"""

from pathlib import Path
from typing import Any

from karaoke_engine.align.activity import vocal_activity, voiced_stretches
from karaoke_engine.align.audio import SAMPLE_RATE, load_mono16k
from karaoke_engine.steps import Transcript, TranscriptSegment

# Apache-2.0. The 1.7B model does not fit a 4 GB card in 16 bits.
MODELS: dict[str, tuple[str, str]] = {
    "0.6b": ("Qwen/Qwen3-ASR-0.6B-hf", "7f1569a48a89f3e3f4dc3a5c9d28bddd903bc76c"),
}
_HOP = 0.02


class QwenTranscriber:
    name = "qwen3-asr"
    version = "1"

    def __init__(
        self,
        model: str = "0.6b",
        stretch_seconds: float = 28.0,
        max_new_tokens: int = 448,
        device: str = "cuda",
    ) -> None:
        if model not in MODELS:
            raise ValueError(f"unknown Qwen3-ASR model '{model}' (use {', '.join(MODELS)})")
        self.model = model
        self.stretch_seconds = stretch_seconds
        self.max_new_tokens = max_new_tokens
        self.device = device
        self._net: Any = None
        self._processor: Any = None

    def load(self) -> None:
        import torch
        from transformers import AutoModelForMultimodalLM, AutoProcessor

        repo, revision = MODELS[self.model]
        # Untyped in transformers, missing without the ml extra: Any either way.
        processor: Any = AutoProcessor
        self._processor = processor.from_pretrained(repo, revision=revision)
        net = AutoModelForMultimodalLM.from_pretrained(
            repo, revision=revision, dtype=torch.bfloat16
        )
        self._net = net.to(self.device).eval()

    def transcribe(self, vocals: Path, language: str) -> Transcript:
        import torch

        if self._net is None:
            self.load()
        samples = load_mono16k(vocals)
        active = vocal_activity(samples, SAMPLE_RATE, _HOP)
        segments = []
        for first, last in voiced_stretches(active, _HOP, limit=self.stretch_seconds):
            clip = samples[round(first * SAMPLE_RATE) : round(last * SAMPLE_RATE)]
            inputs = self._processor.apply_transcription_request(audio=clip, language=language)
            inputs = inputs.to(self._net.device, self._net.dtype)
            with torch.inference_mode():
                out = self._net.generate(
                    **inputs, max_new_tokens=self.max_new_tokens, do_sample=False
                )
            new = out[:, inputs["input_ids"].shape[1] :]
            text = self._processor.decode(new, return_format="transcription_only")[0].strip()
            if text:
                segments.append(TranscriptSegment(first, last, text))
        return Transcript(language=language, segments=tuple(segments))
