"""Text normalization for scoring lyrics, Galician first.

Scores compare words, not formatting: case, punctuation and section labels must not count as
errors, but accents do (in Galician "é" and "e" are different words). Bump
NORMALIZATION_VERSION whenever a rule changes, because it changes every score.
"""

import re
import unicodedata

NORMALIZATION_VERSION = 1

_APOSTROPHES = str.maketrans({"’": "'", "‘": "'", "´": "'", "`": "'"})
_LABEL = re.compile(r"\[[^\]]*\]")
# Repeat marks people add to pasted lyrics: "x2", "x3" with a multiplication sign, "(x2)",
# "(bis)", or "bis" ending a line.
_REPEAT = re.compile(
    r"\(\s*(?:[x\u00d7]\s*\d+|bis)\s*\)|(?<!\w)[x\u00d7]\s?\d+(?!\w)|(?<!\w)bis\s*$",
    re.IGNORECASE | re.MULTILINE,
)
# Hyphen-minus plus the Unicode hyphens and dashes (U+2010 to U+2015).
_DASHES = re.compile(r"[-\u2010-\u2015]")
_LOOSE_APOSTROPHE = re.compile(r"(?<!\w)'|'(?!\w)")
_SPACES = re.compile(r"\s+")
# Galician spellings of one same word: gheada written "j" or "gh" ("janarme", "gherra") and
# seseo ("corasón", "naser"), against "g"/"gu" and "z"/"c".
_GHEADA = re.compile(r"gh|j|gu(?=[ei])")
_SESEO = re.compile(r"z|c(?=[ei])")
# Pronouns that follow their verb in Galician; lyrics sites often write them apart.
_ENCLITICS = frozenset(
    {"che", "lle", "lles", "cho", "cha", "chos", "chas", "llo", "lla", "llos", "llas", "me",
     "te", "vos"}
)  # fmt: skip


def normalize(text: str) -> str:
    """Lowercase words separated by single spaces, ready for WER and CER."""
    text = unicodedata.normalize("NFC", text).lower().translate(_APOSTROPHES)
    text = _strip_marks(text)
    text = _DASHES.sub(" ", text)
    text = "".join(ch if ch.isalnum() or ch.isspace() or ch == "'" else " " for ch in text)
    text = _LOOSE_APOSTROPHE.sub(" ", text)
    return _SPACES.sub(" ", text).strip()


def tokens(text: str) -> list[str]:
    return normalize(text).split()


def fold(token: str) -> str:
    """Drops diacritics, so "línea" and "linea" match when pairing words."""
    decomposed = unicodedata.normalize("NFD", token)
    return unicodedata.normalize(
        "NFC", "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    )


def lenient(text: str, language: str) -> str | None:
    """The words with the spelling choices that are not mistakes folded away; Galician only.

    Lyrics sites write songs the way they sound: gheada ("janarme"), seseo ("corasón"), few
    accents, and pronouns apart from their verb ("deixei che"). A transcriber that writes the
    standard form of the same word heard it right, and a strict WER counts it wrong. Here both
    spellings give the same word, and a pronoun is glued to the word before it on both sides.
    None for a language without such rules.
    """
    if language != "gl":
        return None
    words: list[str] = []
    for token in tokens(text):
        word = _SESEO.sub("s", _GHEADA.sub("g", fold(token)))
        if word in _ENCLITICS and words:
            words[-1] += word
        else:
            words.append(word)
    return " ".join(words)


def match_key(word: str) -> str:
    """Key for pairing a displayed word with a reference word; empty for punctuation only."""
    return fold(normalize(word)).replace(" ", "")


def lyrics_lines(text: str) -> list[str]:
    """Sung lines of pasted lyrics, as displayed: no labels, repeat marks or blank lines."""
    lines = []
    for raw in text.lstrip("﻿").splitlines():
        line = _SPACES.sub(" ", _strip_marks(raw)).strip()
        if any(ch.isalnum() for ch in line):
            lines.append(line)
    return lines


def _strip_marks(text: str) -> str:
    return _REPEAT.sub(" ", _LABEL.sub(" ", text))
