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

from src.guardrails import apply_guardrails
from src.recommender import (
    load_songs,
    prioritise,
    recommend_songs,
    retrieval_boost,
)
from src.retrieval import CulturalIndex, summarise_document

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SONGS_CSV = PROJECT_ROOT / "data" / "songs.csv"

# we use this function if user query doesn't have valid info
# that can help us make a recommendation
def _diverse_sample(songs: List[Dict], k: int) -> List[Dict]:
    """
    Pick up to k songs spread across genres, instead of file order.

    Used when guardrails.apply_guardrails() finds a profile with no usable
    preferences: returning the first k CSV rows would look like a ranking
    without being one. Grouping by genre and taking one song per genre per
    round means the result is at least varied, and the caller is told (via
    strategy="diverse_sample" in the result) that this isn't a ranking.
    """
    # creates a dict grouped by genre
    by_genre: Dict[str, List[Dict]] = {}

    for song in songs:
        # adds new songs by genre
        by_genre.setdefault(song["genre"], []).append(song)
    for group in by_genre.values():
        # sorts the songs
        group.sort(key=lambda s: s["id"])

    genres = sorted(by_genre)
    sample: List[Dict] = []
    
    '''
    Keep selecting songs while:
    We haven't reached k songs, AND
    There are still songs available in at least one genre.
    '''
    round_index = 0
    while len(sample) < k and round_index < max(len(g) for g in by_genre.values()):
        for genre in genres:
            group = by_genre[genre]
            if round_index < len(group):
                sample.append(group[round_index])
                if len(sample) >= k:
                    break
        round_index += 1
    return sample

'''
input: 
user preferences
+ optional cultural/context query

output:
ranked song recommendations
+ information about the cultural retrieval used
+ citations/explanations when available

The important distinction is that retrieval only 
happens if the user provides a context query.

prefs + context_query
        ↓
load songs
        ↓
if there's a context query:
    search cultural corpus
        ↓
    get artist/genre boosts
        ↓
score songs
        ↓
attach cultural citation if relevant
        ↓
return recommendations
'''
def recommend(
    prefs: Dict,
    context_query: Optional[str] = None,
    k: int = 5,
    weights: Optional[Dict[str, float]] = None,
    priorities: Optional[List[str]] = None,
    songs: Optional[List[Dict]] = None,
    index: Optional[CulturalIndex] = None,
) -> Dict:
    """
    Produce recommendations, optionally informed by a free-text context query.

    `priorities` names features the user wants weighted more heavily; the
    weights are rebalanced so the total is unchanged, making it a trade-off
    rather than a volume control. Explicit `weights` take precedence if both
    are given.

    Returns the recommendations together with what retrieval did, so a caller
    can show whether a cultural claim was involved and where it came from.
    An empty retrieval is reported rather than hidden: it means the corpus has
    nothing to say about the query, which the caller may want to act on.
    """
    songs = songs if songs is not None else load_songs(str(SONGS_CSV))
    if weights is None and priorities:
        weights = prioritise(priorities)

    guardrail_result = apply_guardrails(prefs, songs)
    prefs = guardrail_result.prefs

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
    '''
    if query doesn't have relevant info, just recommend a range of diverse songs
    else, recommend songs according to ranking
    '''
    if guardrail_result.unrankable:

        strategy = "diverse_sample"
        # example output: (song2, 0.0, "no preferences given")
        # provides a reason for why song isnt scored
        ranked = [(song, 0.0, "no preferences given") for song in
                  _diverse_sample(songs, k)]
    else:
        strategy = "ranked"
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
        "strategy": strategy,
        # returns issues encountered when guardrail is applied
        "guardrail_issues": [str(issue) for issue in guardrail_result.issues],
        "recommendations": results,
    }

'''
This takes the dictionary produced by recommend() 
and turns it into human-readable terminal output.
'''
def format_result(result: Dict) -> str:
    """Render a recommendation result for the terminal."""
    lines: List[str] = []
    query = result["context_query"]
    lines.append(f"context query: {query!r}" if result["retrieval_used"]
                 else "context query: (none — retrieval disabled)")

    # reports issues encountered when applying a guardrail, ex: clamping a value
    if result["guardrail_issues"]:
        lines.append("guardrails:")
        for issue in result["guardrail_issues"]:
            lines.append(f"    {issue}")

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

    # lets user know if query is unrankable, we are recommending a diverse set of songs 
    # for exploration, no basis for recommendation
    # else, suggest ranked recommendation.
    if result["strategy"] == "diverse_sample":
        lines.append("no usable preferences — diverse sample, not a ranking:")
    else:
        lines.append("recommendations:")
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

'''
its a testing function to check whether cultural retireval improves
recommendations or not

Ex: "ethiopian jazz"
without retrieval → normal feature-based ranking
with retrieval → culturally relevant songs get boosted
'''
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
