"""
Tests for the guardrail layer.

Each test locks in one of the four known v1 scoring bugs recorded in
model_card.md: out-of-range numbers, capitalisation mismatches, unrecognised
values, and empty profiles silently ranking nothing.
"""

from src.guardrails import apply_guardrails

SONGS = [
    {"id": 1, "title": "Fiel", "artist": "Los Legendarios", "genre": "reggaeton",
     "mood": "celebratory", "energy": 0.7, "tempo_bpm": 95.0, "valence": 0.6,
     "danceability": 0.8, "acousticness": 0.2, "region": "Puerto Rico"},
    {"id": 2, "title": "Wave", "artist": "DJ Snow", "genre": "pop",
     "mood": "warm", "energy": 0.5, "tempo_bpm": 110.0, "valence": 0.5,
     "danceability": 0.5, "acousticness": 0.4, "region": "USA"},
]


def test_clamp_numeric_pulls_out_of_range_into_bounds():
    result = apply_guardrails({"energy": 1.5, "valence": -0.3}, SONGS)
    assert result.prefs["energy"] == 1.0
    assert result.prefs["valence"] == 0.0
    actions = {issue.field: issue.action for issue in result.issues}
    assert actions["energy"] == "clamped"
    assert actions["valence"] == "clamped"


def test_clamp_numeric_leaves_in_range_untouched():
    result = apply_guardrails({"danceability": 0.4}, SONGS)
    assert result.prefs["danceability"] == 0.4
    assert result.issues == []


def test_categorical_normalises_case_and_whitespace():
    result = apply_guardrails({"genre": " Pop "}, SONGS)
    assert result.prefs["genre"] == "pop"
    assert result.issues[0].action == "normalised"


def test_categorical_corrects_close_typo():
    result = apply_guardrails({"genre": "reggeaton"}, SONGS)
    assert result.prefs["genre"] == "reggaeton"
    assert result.issues[0].action == "corrected"


def test_categorical_drops_unrecognised_value():
    result = apply_guardrails({"mood": "saad"}, SONGS)
    assert "mood" not in result.prefs
    assert result.issues[0].action == "unknown"


def test_empty_profile_is_flagged_unrankable():
    result = apply_guardrails({}, SONGS)
    assert result.unrankable is True
    assert result.issues[0].action == "blocked"


def test_all_typos_profile_is_flagged_unrankable():
    # Every field here is unrecognisable, so after cleaning there is nothing
    # left to score against — this must be caught the same as a literal {}.
    result = apply_guardrails({"genre": "saad", "mood": "zzz"}, SONGS)
    assert result.prefs == {}
    assert result.unrankable is True


def test_apply_guardrails_collects_every_issue_together():
    result = apply_guardrails(
        {"genre": " Pop ", "mood": "saad", "energy": 2.0}, SONGS,
    )
    actions = sorted(issue.action for issue in result.issues)
    assert actions == ["clamped", "normalised", "unknown"]
    assert result.unrankable is False
