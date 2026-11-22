"""Builds the fonts of the console, from Google Fonts sources pinned to one commit.

Run it only to add or change a font; the results are versioned:

    uv run --no-project --with fonttools --with brotli python scripts/build_web_fonts.py

IBM Plex Sans is variable: one file covers every weight the console uses, limited to them and to
its normal width. IBM Plex Mono, for times and codes, comes as two static weights. Each file is
cut down to Latin, so they stay small.
"""

import shutil
import sys
import urllib.request
from io import BytesIO
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

COMMIT = "86aced91de05cd4f96a06838124cca45be337b2b"
SOURCE = f"https://raw.githubusercontent.com/google/fonts/{COMMIT}"
OUT = Path(__file__).resolve().parents[1] / "web/src/lib/ui/fonts"

# (output stem, google/fonts directory, file, axis limits; None for a static face)
FONTS: list[tuple[str, str, str, dict[str, object] | None]] = [
    # The console's text, headings included.
    (
        "IBMPlexSans",
        "ofl/ibmplexsans",
        "IBMPlexSans[wdth,wght].ttf",
        {"wdth": 100, "wght": (400, 600)},
    ),
    # Times, durations, ids and commands to paste.
    ("IBMPlexMono-Regular", "ofl/ibmplexmono", "IBMPlexMono-Regular.ttf", None),
    ("IBMPlexMono-Medium", "ofl/ibmplexmono", "IBMPlexMono-Medium.ttf", None),
]

# Latin for Galician, Portuguese, Spanish and every other Latin-script language, combining marks,
# general punctuation, the euro, the trade mark sign and arrows for keyboard hints.
UNICODES = [
    *range(0x0020, 0x007F),
    *range(0x00A0, 0x0250),
    *range(0x0300, 0x0370),
    *range(0x1E00, 0x1F00),
    *range(0x2010, 0x2070),
    0x20AC,
    0x2122,
    *range(0x2190, 0x2194),
]


def _download(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=60) as response:  # noqa: S310 - fixed https URL
        data: bytes = response.read()
        return data


def build(stem: str, directory: str, file: str, limits: dict[str, object] | None) -> None:
    font = TTFont(
        BytesIO(_download(f"{SOURCE}/{directory}/{file.replace('[', '%5B').replace(']', '%5D')}"))
    )
    if limits is not None:
        font = instancer.instantiateVariableFont(font, limits)
    # A round trip through bytes loads every table eagerly: the subsetter needs it after instancing.
    buffer = BytesIO()
    font.save(buffer)
    buffer.seek(0)
    font = TTFont(buffer)
    options = subset.Options()
    options.flavor = "woff2"
    options.layout_features = ["*"]
    options.name_IDs = ["*"]
    options.notdef_outline = True
    subsetter = subset.Subsetter(options)
    subsetter.populate(unicodes=UNICODES)
    subsetter.subset(font)
    out = OUT / f"{stem}.woff2"
    font.flavor = "woff2"
    font.save(out)
    licence = _download(f"{SOURCE}/{directory}/OFL.txt")
    (OUT / f"OFL-{stem.split('-')[0]}.txt").write_bytes(licence)
    print(f"{out.name}: {out.stat().st_size / 1024:.0f} kB", file=sys.stderr)


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    for stem, directory, file, limits in FONTS:
        build(stem, directory, file, limits)


if __name__ == "__main__":
    main()
