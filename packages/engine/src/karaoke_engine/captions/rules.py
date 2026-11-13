"""The subtitling rules and the shapes every caption step shares.

The numbers follow the Netflix timed text style guides (general and Castilian Spanish) and the
Spanish standard UNE 153010: two lines of at most 42 characters, a reading speed that leaves time
to read, between five sixths of a second and seven seconds on screen, and a two-frame gap.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Rules:
    max_chars: int = 42  # per line
    max_lines: int = 2
    target_cps: float = 15.0  # characters per second a caption should not exceed
    max_cps: float = 17.0  # beyond this it goes to the review list
    min_duration: float = 5 / 6
    max_duration: float = 7.0
    min_gap_frames: int = 2
    chain_gap: float = 0.5  # gaps shorter than this close to min_gap_frames
    linger: float = 0.5  # how long a caption may stay after its last word
    shot_snap_frames: int = 12  # an edge this close to a cut moves to the cut
    pause_split: float = 0.3  # a pause this long is a good place to start a new caption


@dataclass(frozen=True)
class TimedWord:
    text: str  # as written, with its punctuation attached ("mar,")
    start: float
    end: float
    confidence: float
    speaker: str | None = None


@dataclass(frozen=True)
class Caption:
    start: float
    end: float
    lines: tuple[str, ...]
    speakers: tuple[str | None, ...]  # one per line
    words: tuple[TimedWord, ...] = ()


# Galician words that lean on the next one: a line never ends on them (nor on the Spanish ones
# that slip into colloquial speech). Articles, contractions, prepositions, conjunctions,
# possessives before a noun, unstressed pronouns and the negation that goes before a verb.
_FUNCTION_WORDS = """
o a os as lo la los las un unha uns unhas
do da dos das dun dunha duns dunhas no na nos nas nun nunha nuns nunhas
ao á aos ás ó ós co coa cos coas cun cunha cuns cunhas polo pola polos polas
deste desta destes destas dese desa deses desas daquel daquela daqueles daquelas
neste nesta nestes nestas nese nesa neses nesas naquel naquela naqueles naquelas
de en con por para sen sobre entre ante ata até baixo contra desde dende tras cara so
e ou nin pero mais que se como cando porque pois
meu miña meus miñas teu túa teus túas seu súa seus súas
me te lle lles vos che mo ma cho cha llo lla
non
el y del al una unos unas
"""
FUNCTION_WORDS: frozenset[str] = frozenset(_FUNCTION_WORDS.split())
