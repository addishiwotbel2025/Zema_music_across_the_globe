"""
Tests for retrieval and its effect on ranking.

Unit tests build a tiny in-memory corpus so they run without the network and
without data/cultural_notes.jsonl. The integration tests at the bottom use the
real files and skip if those have not been generated yet.
"""

import pytest

from src.recommender import RETRIEVAL_WEIGHT, recommend_songs, retrieval_boost
from src.retrieval import CulturalIndex, summarise_document


def make_index() -> CulturalIndex:
    """A three-document corpus with deliberately distinct vocabulary."""
    return CulturalIndex([
        {
            "doc_id": "wiki:Ethio-jazz",
            "wiki_title": "Ethio-jazz",
            "url": "https://example.org/ethio",
            "strategy": "exact",
            "extract": (
                "Ethiopian jazz, also called Ethio-jazz, blends traditional "
                "Ethiopian pentatonic melodies with jazz harmony and Latin "
                "rhythm. Mulatu Astatke pioneered the style in Addis Ababa."
            ),
            "matches": [{"kind": "genre", "name": "ethio-jazz"}],
        },
        {
            "doc_id": "wiki:Mulatu Astatke",
            "wiki_title": "Mulatu Astatke",
            "url": "https://example.org/mulatu",
            "strategy": "exact",
            "extract": (
                "Mulatu Astatke is an Ethiopian musician and arranger "
                "considered the father of Ethio-jazz. He studied vibraphone "
                "and percussion in London and Boston."
            ),
            "matches": [{"kind": "artist", "name": "Mulatu Astatke"}],
        },
        {
            "doc_id": "wiki:Flamenco",
            "wiki_title": "Flamenco",
            "url": "https://example.org/flamenco",
            "strategy": "exact",
            "extract": (
                "Flamenco is an art form based on folkloric traditions of "
                "southern Spain, built on guitar playing, singing and dance "
                "developed within the gitano communities of Andalusia."
            ),
            "matches": [{"kind": "genre", "name": "flamenco"}],
        },
    ])


SONGS = [
    {"id": 1, "title": "Tezeta", "artist": "Mulatu Astatke", "genre": "ethio-jazz",
     "mood": "warm", "energy": 0.35, "tempo_bpm": 88.0, "valence": 0.55,
     "danceability": 0.45, "acousticness": 0.60, "region": "Ethiopia"},
    {"id": 2, "title": "Entre Dos Aguas", "artist": "Paco de Lucía",
     "genre": "flamenco", "mood": "celebratory", "energy": 0.55,
     "tempo_bpm": 120.0, "valence": 0.65, "danceability": 0.60,
     "acousticness": 0.80, "region": "Spain"},
    {"id": 3, "title": "Dancing Queen", "artist": "ABBA", "genre": "swedish",
     "mood": "celebratory", "energy": 0.60, "tempo_bpm": 101.0, "valence": 0.80,
     "danceability": 0.75, "acousticness": 0.15, "region": "Sweden"},
]


# --- searching ------------------------------------------------------------

def test_search_ranks_the_topically_closest_document_first():
    hits = make_index().search("ethiopian jazz")
    assert hits, "expected at least one match"
    assert hits[0][0]["wiki_title"] == "Ethio-jazz"


def test_search_returns_nothing_for_an_unrelated_query():
    # An empty result is a valid answer: the corpus has nothing on this.
    assert make_index().search("norwegian black metal drumming") == []


def test_empty_query_returns_nothing_rather_than_everything():
    index = make_index()
    assert index.search("") == []
    assert index.search("   ") == []


def test_scores_are_ordered_descending():
    hits = make_index().search("spanish guitar and dance")
    scores = [score for _, score in hits]
    assert scores == sorted(scores, reverse=True)


# --- mapping documents back to songs --------------------------------------

def test_boosts_are_keyed_by_kind_and_name():
    boosts = make_index().boosts("ethiopian jazz")
    assert ("genre", "ethio-jazz") in boosts
    assert boosts[("genre", "ethio-jazz")]["score"] > 0
    assert "document" in boosts[("genre", "ethio-jazz")]


def test_boost_applies_to_a_song_by_artist_or_by_genre():
    boosts = make_index().boosts("flamenco guitar from andalusia")
    score, match = retrieval_boost(SONGS[1], boosts)
    assert score > 0
    assert match["document"]["wiki_title"] == "Flamenco"


def test_unmatched_song_gets_no_boost():
    boosts = make_index().boosts("ethiopian jazz")
    score, match = retrieval_boost(SONGS[2], boosts)  # ABBA
    assert score == 0.0
    assert match is None


def test_no_boosts_argument_is_harmless():
    assert retrieval_boost(SONGS[0], None) == (0.0, None)
    assert retrieval_boost(SONGS[0], {}) == (0.0, None)


def test_song_matching_both_artist_and_genre_is_boosted_once_by_the_stronger():
    # Mulatu matches on genre (ethio-jazz) and artist (Mulatu Astatke). The
    # song must not collect both, or one query would count twice.
    boosts = make_index().boosts("ethiopian jazz")
    score, _ = retrieval_boost(SONGS[0], boosts)
    both = [boosts.get(("genre", "ethio-jazz")), boosts.get(("artist", "Mulatu Astatke"))]
    strongest = max(b["score"] for b in both if b)
    assert score == pytest.approx(strongest)


# --- the behavioural claim ------------------------------------------------

def test_retrieval_changes_the_ranking():
    """
    The claim the whole feature rests on: the same profile produces a
    different order once a context query is supplied.
    """
    prefs = {"energy": 0.6}

    without = [song["title"] for song, _, _ in recommend_songs(prefs, SONGS, k=3)]
    boosts = make_index().boosts("ethiopian jazz")
    with_rag = [song["title"] for song, _, _
                in recommend_songs(prefs, SONGS, k=3, boosts=boosts)]

    assert without[0] != "Tezeta", "energy alone should not favour Tezeta"
    assert with_rag[0] == "Tezeta", "retrieval should lift the Ethiopian track"
    assert without != with_rag


def test_boost_is_added_to_the_score_not_substituted_for_it():
    prefs = {"genre": "flamenco"}
    plain, _ = recommend_songs(prefs, [SONGS[1]], k=1)[0][1], None
    boosts = make_index().boosts("flamenco guitar from andalusia")
    boosted = recommend_songs(prefs, [SONGS[1]], k=1, boosts=boosts)[0][1]
    # The genre match still counts; retrieval only adds on top of it.
    assert boosted > plain
    expected = boosts[("genre", "flamenco")]["score"] * RETRIEVAL_WEIGHT
    assert boosted == pytest.approx(plain + expected)


def test_retrieval_reason_names_the_source_document():
    boosts = make_index().boosts("ethiopian jazz")
    _, _, explanation = recommend_songs({}, [SONGS[0]], k=1, boosts=boosts)[0]
    assert "Ethio-jazz" in explanation


# --- summarising ----------------------------------------------------------

def test_summarise_shortens_long_extracts():
    long_text = "First sentence here. " + ("padding words " * 40)
    assert len(summarise_document({"extract": long_text}, max_chars=80)) <= 81


def test_summarise_leaves_short_extracts_alone():
    text = "Mulatu Astatke is an Ethiopian musician."
    assert summarise_document({"extract": text}) == text


# --- integration, against the real generated files ------------------------

def _real_index():
    try:
        return CulturalIndex.from_file()
    except FileNotFoundError:
        pytest.skip("corpus not built; run python -m src.build_corpus")


def test_real_corpus_finds_ethiopian_jazz():
    hits = _real_index().search("ethiopian jazz")
    assert hits
    assert "Ethio-jazz" in hits[0][0]["wiki_title"]


def test_real_corpus_documents_all_carry_a_source_url():
    for document in _real_index().documents:
        assert document["url"].startswith("http"), document["wiki_title"]


def test_real_corpus_has_no_disambiguation_leftovers():
    """
    Regression test. The salsa entry was once the article about the sauce, and
    the Alonzo entry was a list of people with that name.
    """
    for document in _real_index().documents:
        lowered = document["extract"].lower()
        assert "notable people with the" not in lowered, document["wiki_title"]
        assert "may refer to:" not in lowered[:200], document["wiki_title"]
        assert "most often refers to" not in lowered[:200], document["wiki_title"]
