"""
Tests for user-selectable feature priorities.

The property under test throughout is that prioritising is a *trade-off*: the
total weight is fixed, so favouring one feature must cost the others.
"""

import pytest

from src.recommender import DEFAULT_WEIGHTS, prioritise, recommend_songs

TOTAL = sum(DEFAULT_WEIGHTS.values())

SONGS = [
    # Same genre and mood; they differ only in danceability and energy, so a
    # change in the relative weight of those two decides the order.
    {"id": 1, "title": "Dancey", "artist": "A", "genre": "afrobeats",
     "mood": "celebratory", "energy": 0.50, "tempo_bpm": 110.0, "valence": 0.60,
     "danceability": 0.95, "acousticness": 0.20, "region": "Nigeria"},
    {"id": 2, "title": "Energetic", "artist": "B", "genre": "afrobeats",
     "mood": "celebratory", "energy": 0.90, "tempo_bpm": 130.0, "valence": 0.60,
     "danceability": 0.30, "acousticness": 0.20, "region": "Nigeria"},
]


def test_no_priorities_returns_the_defaults():
    assert prioritise([]) == DEFAULT_WEIGHTS


def test_total_weight_is_preserved():
    for choice in (["genre"], ["mood", "energy"], ["artist", "acousticness"]):
        assert sum(prioritise(choice).values()) == pytest.approx(TOTAL)


def test_prioritised_feature_rises_and_the_others_fall():
    weights = prioritise(["danceability"])
    assert weights["danceability"] > DEFAULT_WEIGHTS["danceability"]
    for name in DEFAULT_WEIGHTS:
        if name != "danceability":
            assert weights[name] < DEFAULT_WEIGHTS[name]


def test_prioritising_everything_changes_nothing():
    """
    Not a bug: if every feature is preferred, none has been preferred. The
    renormalisation makes that explicit instead of inflating every score.
    """
    weights = prioritise(list(DEFAULT_WEIGHTS))
    for name, value in DEFAULT_WEIGHTS.items():
        assert weights[name] == pytest.approx(value)


def test_relative_ordering_within_the_unprioritised_group_is_unchanged():
    weights = prioritise(["artist"])
    # genre started above mood; it must still be above mood afterwards.
    assert weights["genre"] > weights["mood"] > weights["acousticness"]


def test_duplicate_names_are_not_applied_twice():
    assert prioritise(["mood", "mood"]) == pytest.approx(prioritise(["mood"]))


def test_unknown_feature_raises_rather_than_being_ignored():
    with pytest.raises(ValueError) as excinfo:
        prioritise(["enrgy"])
    # The message has to name the offending field and the valid options,
    # otherwise the caller cannot correct it.
    assert "enrgy" in str(excinfo.value)
    assert "energy" in str(excinfo.value)


def test_a_custom_base_is_respected():
    base = {"genre": 1.0, "mood": 1.0}
    weights = prioritise(["genre"], base=base)
    assert sum(weights.values()) == pytest.approx(2.0)
    assert weights["genre"] > weights["mood"]


def test_priorities_change_the_ranking():
    """The behavioural claim: choosing a priority reorders the results."""
    prefs = {"genre": "afrobeats", "mood": "celebratory",
             "energy": 0.9, "danceability": 0.95}

    dance_first = recommend_songs(prefs, SONGS, k=2,
                                  weights=prioritise(["danceability"]))
    energy_first = recommend_songs(prefs, SONGS, k=2,
                                   weights=prioritise(["energy"]))

    assert dance_first[0][0]["title"] == "Dancey"
    assert energy_first[0][0]["title"] == "Energetic"


def test_retrieval_weight_is_not_part_of_the_priority_pool():
    """
    Cultural relevance is a separate dial. At 10.0 against taste weights
    totalling 12.0, folding it in would let it absorb most of the budget.
    """
    assert "retrieval" not in DEFAULT_WEIGHTS
    with pytest.raises(ValueError):
        prioritise(["retrieval"])
