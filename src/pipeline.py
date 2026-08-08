"""
The recommendation pipeline: the stage that ties retrieval to scoring.

Run from the project root:

    python -m src.pipeline

recommender.py scores songs and knows nothing about Wikipedia. retrieval.py
searches text and knows nothing about songs. This module connects them:

    user preferences + optional context query
        -> retrieve   search the cultural corpus for the context query
        -> score      weighted feature match, plus a boost for retrieved
                      artists and genres
        -> explain    reasons, with a quotation and source URL for any
                      cultural claim

Retrieval is what lets the system answer something its columns do not encode.
"ethiopian jazz" is not a value in any field of data/songs.csv, so without
retrieval the request is simply ignored. With it, Mulatu Astatke rises.

Nothing here touches the network, and no API key is used anywhere in this
project. The corpus was fetched once by build_corpus.py and is read from disk.
"""

from pathlib import Path
from typing import Dict, List, Optional

from src.recommender import load_songs, recommend_songs, retrieval_boost
from src.retrieval import CulturalIndex, summarise_document

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SONGS_CSV = PROJECT_ROOT / "data" / "songs.csv"


def recommend(
    prefs: Dict,
    context_query: Optional[str] = None,
    k: int = 5,
    weights: Optional[Dict[str, float]] = None,
    songs: Optional[List[Dict]] = None,
    index: Optional[CulturalIndex] = None,
) -> Dict:
    """
    Produce recommendations, optionally informed by a free-text context query.

    Returns the recommendations together with what retrieval did, so a caller
    can show whether a cultural claim was involved and where it came from.
    An empty retrieval is reported rather than hidden: it means the corpus has
    nothing to say about the query, which the caller may want to act on.
    """
    songs = songs if songs is not None else load_songs(str(SONGS_CSV))

    boosts: Dict = {}
    retrieved: List[Dict] = []
    if context_query and context_query.strip():
        index = index or CulturalIndex.from_file()
        boosts = index.boosts(context_query)
        retrieved = [
            {"title": document["wiki_title"], "score": round(score, 3),
             "url": document["url"], "strategy": document["strategy"]}
            for document, score in index.search(context_query)
        ]

    ranked = recommend_songs(prefs, songs, k=k, weights=weights, boosts=boosts)

    results: List[Dict] = []
    for song, score, _ in ranked:
        _, match = retrieval_boost(song, boosts)
        citation = None
        if match is not None:
            document = match["document"]
            citation = {
                "title": document["wiki_title"],
                "url": document["url"],
                # Quoting the retrieved passage rather than paraphrasing it
                # keeps every cultural claim traceable to its source.
                "quote": summarise_document(document),
                "similarity": round(match["score"], 3),
            }
        results.append({"song": song, "score": score, "citation": citation})

    return {
        "context_query": context_query,
        "retrieval_used": bool(context_query and context_query.strip()),
        "retrieved": retrieved,
        "recommendations": results,
    }


def format_result(result: Dict) -> str:
    """Render a recommendation result for the terminal."""
    lines: List[str] = []
    query = result["context_query"]
    lines.append(f"context query: {query!r}" if result["retrieval_used"]
                 else "context query: (none — retrieval disabled)")

    if result["retrieval_used"]:
        if result["retrieved"]:
            lines.append("retrieved:")
            for hit in result["retrieved"]:
                lines.append(f"    {hit['score']:.3f}  {hit['title']}")
        else:
            # Not an error. The corpus genuinely has nothing on this topic, and
            # saying so is better than quietly returning an unrelated match.
            lines.append("retrieved: nothing above the similarity threshold")

    lines.append("")
    for position, item in enumerate(result["recommendations"], start=1):
        song = item["song"]
        lines.append(f"  {position}. {song['title']} — {song['artist']}")
        lines.append(f"     {song['genre']} · {song['region']} · "
                     f"{song['mood']} · score {item['score']:.2f}")
        if item["citation"]:
            citation = item["citation"]
            lines.append(f"     cultural note ({citation['similarity']:.3f}) "
                         f"— {citation['title']}")
            lines.append(f"       \"{citation['quote']}\"")
            lines.append(f"       {citation['url']}")
    return "\n".join(lines)


def _compare(prefs: Dict, query: str, songs: List[Dict],
             index: CulturalIndex) -> None:
    """
    Show the same profile with retrieval off, then on.

    This is the evidence that retrieval is integrated rather than decorative:
    the two rankings differ, and they differ because of the corpus.
    """
    print("=" * 74)
    print(f"PROFILE {prefs}")
    print(f"QUERY   {query!r}")
    print("=" * 74)
    print("\n--- retrieval OFF ---")
    print(format_result(recommend(prefs, None, songs=songs, index=index)))
    print("\n--- retrieval ON ---")
    print(format_result(recommend(prefs, query, songs=songs, index=index)))
    print()


def main() -> None:
    songs = load_songs(str(SONGS_CSV))
    index = CulturalIndex.from_file()
    print(f"catalog: {len(songs)} songs   corpus: {len(index.documents)} documents\n")

    _compare({"energy": 0.5}, "ethiopian jazz", songs, index)
    _compare({"energy": 0.7, "mood": "celebratory"},
             "flamenco and spanish guitar", songs, index)
    # A query the corpus cannot answer: artist biographies say who someone is,
    # rarely what a song is about. The empty result is reported, not disguised.
    _compare({"energy": 0.6}, "music for a wedding celebration", songs, index)


if __name__ == "__main__":
    main()
