"""
Tests for catalog construction.

Most of these are regression tests for bugs that actually reached the catalog
during development, which is why they are worth keeping: each one describes a
wrong row that was previously written out.
"""

import csv
from pathlib import Path

import pytest

from src.build_catalog import (
    ARTIST_ALLOWLIST,
    VERIFIED_GENRES,
    clean_row,
    derive_mood,
    match_allowlist,
    primary_artist,
)

CATALOG = Path(__file__).resolve().parent.parent / "data" / "songs.csv"


def raw(**overrides) -> dict:
    """A well-formed source row, with fields overridable per test."""
    row = {
        "artists": "Fela Kuti", "track_name": "Zombie", "popularity": "41",
        "energy": "0.70", "valence": "0.45", "danceability": "0.72",
        "acousticness": "0.20", "tempo": "124.0",
    }
    row.update(overrides)
    return row


# --- mood derivation ------------------------------------------------------

@pytest.mark.parametrize("valence,energy,expected", [
    (0.9, 0.9, "celebratory"),
    (0.9, 0.2, "warm"),
    (0.1, 0.9, "intense"),
    (0.1, 0.2, "melancholic"),
    # Exactly on both boundaries, to pin the inclusive comparisons down.
    (0.5, 0.6, "celebratory"),
    (0.49, 0.59, "melancholic"),
])
def test_derive_mood_quadrants(valence, energy, expected):
    assert derive_mood(valence, energy) == expected


# --- artist matching ------------------------------------------------------

def test_allowlisted_artist_is_matched_when_they_lead():
    assert match_allowlist("Fela Kuti") == "Fela Kuti"
    assert match_allowlist("Fela Kuti;Afrika 70") == "Fela Kuti"


def test_featured_guest_does_not_claim_the_track():
    """
    Regression: "Sete" is credited to BLOND:ISH;Francis Mercier;Amadou &
    Mariam. Accepting any credited artist filed a house track as Malian mande.
    """
    assert match_allowlist("BLOND:ISH;Francis Mercier;Amadou & Mariam") is None
    # And a Drake track that merely credits Wizkid is not a Wizkid track.
    assert match_allowlist("Drake;Wizkid;Kyla") is None


def test_matching_is_exact_not_substring():
    """
    Regression: a substring search paired "The HU" with "The Human League",
    which would have filed a synth-pop track as Mongolian folk metal.
    """
    assert "The HU" in ARTIST_ALLOWLIST
    assert match_allowlist("The Human League") is None


def test_primary_artist_takes_the_first_credit():
    assert primary_artist("Wizkid;Tems") == "Wizkid"
    assert primary_artist("  Rema ;Selena Gomez") == "Rema"


# --- row cleaning ---------------------------------------------------------

def test_valid_row_is_parsed_into_numbers():
    values = clean_row(raw())
    assert values["energy"] == 0.70
    assert values["tempo_bpm"] == 124.0
    assert isinstance(values["popularity"], int)


def test_zero_tempo_is_rejected():
    assert clean_row(raw(tempo="0.0")) is None


def test_missing_core_text_is_rejected():
    assert clean_row(raw(artists="")) is None
    assert clean_row(raw(track_name="   ")) is None


def test_unparseable_numbers_are_rejected():
    assert clean_row(raw(energy="n/a")) is None
    assert clean_row(raw(valence="")) is None


# --- the generated catalog ------------------------------------------------

def load_catalog():
    if not CATALOG.exists():
        pytest.skip("catalog not built; run python -m src.build_catalog")
    with open(CATALOG, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_catalog_has_no_duplicate_songs():
    """
    Regression: deduplicating on track_id alone let Baris Manco's
    "Kol Dugmeleri" in twice, because remasters carry different ids.
    """
    rows = load_catalog()
    keys = [(r["title"].lower(), r["artist"].lower()) for r in rows]
    assert len(keys) == len(set(keys))


def test_catalog_features_are_within_range():
    for row in load_catalog():
        for field in ("energy", "valence", "danceability", "acousticness"):
            assert 0.0 <= float(row[field]) <= 1.0, f"{row['title']}: {field}"
        assert float(row["tempo_bpm"]) > 0, row["title"]


def test_every_row_records_how_it_was_selected():
    for row in load_catalog():
        assert row["source"] in {"genre-label", "artist-allowlist"}


def test_allowlisted_rows_carry_their_hand_assigned_region():
    for row in load_catalog():
        if row["source"] != "artist-allowlist":
            continue
        genre, region = ARTIST_ALLOWLIST[row["artist"]]
        assert row["genre"] == genre
        assert row["region"] == region


def test_genre_label_rows_only_use_verified_genres():
    for row in load_catalog():
        if row["source"] == "genre-label":
            assert row["genre"] in VERIFIED_GENRES


def test_catalog_is_culturally_spread():
    """The point of the catalog: no single region should dominate it."""
    rows = load_catalog()
    counts: dict = {}
    for row in rows:
        counts[row["region"]] = counts.get(row["region"], 0) + 1
    assert len(counts) >= 15, f"only {len(counts)} regions"
    assert max(counts.values()) / len(rows) < 0.25
