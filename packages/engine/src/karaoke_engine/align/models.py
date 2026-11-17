"""The CTC models the aligner can use, pinned to a revision, and the default per language.

Defaults are chosen with the bench (decisions 005 and 019). A language without a model of its
own gets the model trained on songs when it can write the lyrics, and otherwise Omnilingual,
which knows the letters of some 1600 languages.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CtcModelSpec:
    repo: str
    revision: str
    licence: str
    # Letters the model never saw, written as the closest letter it knows.
    fallbacks: dict[str, str] = field(default_factory=dict)
    # A big checkpoint published in 32 bits: it is stored once in 16 bits in the model cache
    # and loaded from there, at half the memory (emissions.half_copy).
    half: bool = False


_GL_FALLBACKS = {"ç": "z", "ï": "i", "ü": "u"}

MODELS: dict[str, CtcModelSpec] = {
    "nos-xlsr-300m-gl": CtcModelSpec(
        "proxectonos/Nos_ASR-wav2vec2-xls-r-300m-gl",
        "05a9b49121aadff50c84bb78fa9462769c8b17d8",
        "Apache-2.0",
        _GL_FALLBACKS,
    ),
    "nos-w2vbert-gl": CtcModelSpec(
        "proxectonos/w2v-bert-2.0-gl",
        "3d09a7bb744413285c423ac41efa06b4d79e1fdd",
        "Apache-2.0",
        _GL_FALLBACKS,
    ),
    # w2v-BERT 2.0 pretrained further on music and trained on whole-song lyrics: sung letters in
    # any language its 921 characters write.
    "music-w2vbert-ctc": CtcModelSpec(
        "mrfakename/w2v-bert-2.0-music-lyrics-ctc",
        "1be91455793f86de803ac0707303a0998e423ce1",
        "MIT",
        half=True,
    ),
    # Omnilingual ASR CTC (Meta, Apache-2.0), converted to Wav2Vec2ForCTC.
    "omni-ctc-300m": CtcModelSpec(
        "aadel4/omniASR-CTC-300M-v2", "f2b3c39a62c061c27623c3f2d803294fbb954324", "Apache-2.0"
    ),
    "omni-ctc-1b": CtcModelSpec(
        "aadel4/omniASR-CTC-1B-v2", "966cb4b90c2322ebe0f344ebb5da4ed938fde7b2", "Apache-2.0"
    ),
    # No licence stated: only for comparisons in the bench, never a default.
    "ifrz-gl": CtcModelSpec(
        "ifrz/wav2vec2-large-xlsr-galician",
        "70b3bfad73c9cec3b2c638c655bc6dc7ceef2c9e",
        "unknown",
        _GL_FALLBACKS,
    ),
    "w2v2-en": CtcModelSpec(
        "facebook/wav2vec2-base-960h", "22aad52d435eb6dbaf354bdad9b0da84ce7d6156", "Apache-2.0"
    ),
    "w2v2-large-en": CtcModelSpec(
        "facebook/wav2vec2-large-960h-lv60-self",
        "54074b1c16f4de6a5ad59affb4caa8f2ea03a119",
        "Apache-2.0",
    ),
    "xlsr-en": CtcModelSpec(
        "jonatasgrosman/wav2vec2-large-xlsr-53-english",
        "569a6236e92bd5f7652a0420bfe9bb94c5664080",
        "Apache-2.0",
    ),
    "xlsr-es": CtcModelSpec(
        "jonatasgrosman/wav2vec2-large-xlsr-53-spanish",
        "96d7e9b4e4a78af515a3c6d3cee7c0826045d276",
        "Apache-2.0",
    ),
    "xlsr-fr": CtcModelSpec(
        "jonatasgrosman/wav2vec2-large-xlsr-53-french",
        "7c79e105a6525d38e1e69f640b974b4a679723cc",
        "Apache-2.0",
    ),
    "xlsr-de": CtcModelSpec(
        "jonatasgrosman/wav2vec2-large-xlsr-53-german",
        "4b8a02957378d0f2da2ef74091156b032c485a89",
        "Apache-2.0",
    ),
    "xlsr-pt": CtcModelSpec(
        "jonatasgrosman/wav2vec2-large-xlsr-53-portuguese",
        "634ac655299bcdc46c83bc01da9bab52d2987e4f",
        "Apache-2.0",
    ),
}

DEFAULT_BY_LANGUAGE: dict[str, str] = {
    "gl": "nos-xlsr-300m-gl",
    "en": "w2v2-large-en",
    "es": "xlsr-es",
    "fr": "xlsr-fr",
    "de": "xlsr-de",
    "pt": "xlsr-pt",
}
# A second model whose emissions are averaged with the language's own (emissions.blend): trained
# on songs, it hears what a speech model misses (decision 019). None for none.
DEFAULT_SECOND: str | None = "music-w2vbert-ctc"
# For songs in any other language: trained on music in many languages, it aligns as well as a
# language's own speech model (99.4 % against Omnilingual's 91.4 % on the quick set).
FALLBACK_MODEL = "music-w2vbert-ctc"
# For lyrics in letters the music model does not have, and for speech (interview captions).
WIDE_FALLBACK_MODEL = "omni-ctc-300m"
