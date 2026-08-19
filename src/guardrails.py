"""
Guardrails: checks applied to input before scoring, and to output after it.

The governing rule is **fix, but disclose**. Every correction made here is
recorded and handed back to the caller so it can be shown. A guardrail that
quietly rewrites input is only a different bug: the user gets results they did
not ask for, with no way to find out why.

Nothing here needs a network or an API key.
"""

import difflib
from dataclasses import dataclass, field as _dataclass_field
from typing import Any, Dict, List, Set


@dataclass
class Issue:
    """
    One thing a guardrail changed, refused, or noticed.

    `action` is one of:
        clamped     a number outside its allowed range was pulled back in
        normalised  text was lowercased or had whitespace tidied
        corrected   an unrecognised value was replaced with a close match
        unknown     a value could not be understood and was ignored
        blocked     something was withheld from the results

    action: what the guardrail did

    example:
        Issue(
        field="volume",
        action="clamped",
        original=150,
        resolved=100,
        message="Volume was too high."
)
    """
    field: str
    action: str
    original: Any
    resolved: Any = None
    message: str = ""

    def __str__(self) -> str:
        return self.message or f"{self.field}: {self.action}"


def _known_values(songs: List[Dict], field_name: str) -> Set[str]:
    """The distinct real values a field takes across the loaded catalog."""
    return {song[field_name] for song in songs if song.get(field_name)}


# makes sure that features are in range
_RANGE_FIELDS = ("energy", "valence", "danceability")


def _clamp_numeric(prefs: Dict, issues: List[Issue]) -> Dict:
    """Pull energy/valence/danceability targets back into [0.0, 1.0]."""
    cleaned = dict(prefs)
    for name in _RANGE_FIELDS:
        value = cleaned.get(name)
        if value is None or not isinstance(value, (int, float)):
            continue
        if 0.0 <= value <= 1.0:
            continue
        # clamping values
        resolved = max(0.0, min(1.0, float(value)))
        issues.append(Issue(
            field=name, action="clamped", original=value, resolved=resolved,
            message=f"{name} of {value} is outside 0.0-1.0; clamped to {resolved}.",
        ))
        # dict updated with reclamped value
        cleaned[name] = resolved
    return cleaned



_CATEGORICAL_FIELDS = ("genre", "mood", "artist")

# How close a misspelled value has to be to a real one (0-1 similarity from
# difflib) before it's auto-corrected rather than treated as unrecognisable.
# 0.6 catches "afrobeat" -> "afrobeats" without also matching two genres that
# just happen to share a few letters.
_FUZZY_CUTOFF = 0.6

# guardrail for capitalization and whitespace
def _resolve_categorical(prefs: Dict, songs: List[Dict],
                          issues: List[Issue]) -> Dict:
    """Match genre/mood/artist preferences against real catalog values."""
    cleaned = dict(prefs)
    for name in _CATEGORICAL_FIELDS:
        raw = cleaned.get(name)
        if not raw or not isinstance(raw, str):
            continue

        known = _known_values(songs, name)
        by_lower = {value.lower(): value for value in known}
        tidied = raw.strip().lower()

        if tidied in by_lower:
            resolved = by_lower[tidied]
            if resolved != raw:
                issues.append(Issue(
                    field=name, action="normalised", original=raw,
                    resolved=resolved,
                    message=f"{name} {raw!r} normalised to {resolved!r}.",
                ))
            cleaned[name] = resolved
            continue

        close = difflib.get_close_matches(
            tidied, by_lower.keys(), n=1, cutoff=_FUZZY_CUTOFF,
        )
        if close:
            resolved = by_lower[close[0]]
            issues.append(Issue(
                field=name, action="corrected", original=raw,
                resolved=resolved,
                message=f"{name} {raw!r} was not recognised; using closest "
                        f"match {resolved!r}.",
            ))
            cleaned[name] = resolved
        else:
            issues.append(Issue(
                field=name, action="unknown", original=raw, resolved=None,
                message=f"{name} {raw!r} was not recognised and could not "
                        f"be matched to a known value; ignored.",
            ))
            del cleaned[name]
    return cleaned



_SIGNAL_FIELDS = (
    "genre", "mood", "artist", "energy", "valence", "danceability",
    "likes_acoustic",
)

# function checks whether if there is any relevant information in a user's 
# query that can help us make recommendations
# if there is enough info, return False, else True
# ex: if any of the strings are found in _signal_fields, it returns False since there is enough 
# info to give recommendation to the user
def _check_unrankable(prefs: Dict, issues: List[Issue]) -> bool:
    """True if `prefs` has no usable signal left to score songs against."""
    # if string in _signal_fields:
    has_signal = any(prefs.get(name) is not None for name in _SIGNAL_FIELDS)
    if has_signal:
        return False
    issues.append(Issue(
        field="profile", action="blocked", original=dict(prefs),
        resolved=None,
        message="No usable preferences were given; returning a diverse "
                "sample instead of a ranking.",
    ))
    return True

# GuradrailResult carries information about the issue, cleaned data and whether 
# user query can be used for recommendation
@dataclass
class GuardrailResult:
    # prefs will contain a cleaned query (free from all errors)
    prefs: Dict
    # new list generated for every issue
    issues: List[Issue] = _dataclass_field(default_factory=list)
    # is user query valid enough to recommend a music?
    unrankable: bool = False


def apply_guardrails(prefs: Dict, songs: List[Dict]) -> GuardrailResult:
    """
    Clean a raw preferences dict before it reaches scoring.

    Runs the three checks in order: numeric clamping, then categorical
    matching (which can itself drop a field), then the emptiness check — so a
    profile that turns out to be nothing but typos is correctly caught as
    unrankable, not just a literally empty `{}`.
    """
    issues: List[Issue] = []
    cleaned = _clamp_numeric(prefs, issues)
    cleaned = _resolve_categorical(cleaned, songs, issues)
    unrankable = _check_unrankable(cleaned, issues)
    return GuardrailResult(prefs=cleaned, issues=issues, unrankable=unrankable)
