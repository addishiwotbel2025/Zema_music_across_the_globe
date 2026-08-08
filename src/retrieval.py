"""
Retrieval over the cultural corpus.

The scorer in recommender.py compares numbers: is this song's energy near the
one the user asked for? That cannot answer "something political", because there
is no political column and there never will be one.

This module searches text instead. It indexes the Wikipedia extracts collected
by build_corpus.py and, given a free-text query, returns the articles that best
match it — then maps those articles back to the artists and genres they
describe, so songs can be boosted.

Method: TF-IDF with cosine similarity.

  TF   how often a word appears in this document
  IDF  how rare that word is across every document
  TF x IDF  scores a word highly only when it is frequent here and rare
            elsewhere, which is what makes it characteristic of a document

Cosine similarity then compares the *direction* of the query and document
vectors rather than the distance between them, so a long article is not
penalised for being long.

No network access and no API key: this reads the .jsonl file from disk.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CORPUS_JSONL = PROJECT_ROOT / "data" / "cultural_notes.jsonl"

# Below this, a "match" is a handful of incidental shared words rather than a
# real topical hit. Returning those would let the system attach a confident
# cultural explanation to a song the query had nothing to do with.
MIN_SIMILARITY = 0.05


class CulturalIndex:
    """A searchable index over the cultural corpus."""

    def __init__(self, documents: List[Dict]):
        self.documents = documents
        # The article title is prepended to its own text so that a query naming
        # an artist or genre directly ("fela kuti") matches strongly, not just
        # queries about themes.
        corpus = [
            f"{doc['wiki_title']}. {doc['extract']}" for doc in documents
        ]
        self._vectorizer = TfidfVectorizer(
            stop_words="english",
            # Words appearing in almost every document (like "music") carry no
            # discriminating power, so they are dropped outright.
            max_df=0.85,
            # Sublinear scaling: a word occurring ten times is more meaningful
            # than one occurring once, but not ten times more.
            sublinear_tf=True,
            # Unigrams and bigrams, so "military rule" is a term in its own
            # right and not only two separate words.
            ngram_range=(1, 2),
        )
        self._matrix = self._vectorizer.fit_transform(corpus)

    @classmethod
    def from_file(cls, path: Path = CORPUS_JSONL) -> "CulturalIndex":
        if not path.exists():
            raise FileNotFoundError(
                f"Missing {path}. Run: python -m src.build_corpus"
            )
        with open(path, encoding="utf-8") as f:
            documents = [json.loads(line) for line in f if line.strip()]
        return cls(documents)

    def search(self, query: str, top_k: int = 5) -> List[Tuple[Dict, float]]:
        """
        Return the (document, similarity) pairs best matching the query.

        An empty result is a real answer, not a failure: it means nothing in
        the corpus is about what was asked.
        """
        if not query or not query.strip():
            return []
        query_vector = self._vectorizer.transform([query])
        scores = cosine_similarity(query_vector, self._matrix)[0]
        ranked = sorted(enumerate(scores), key=lambda pair: pair[1], reverse=True)
        return [
            (self.documents[index], float(score))
            for index, score in ranked[:top_k]
            if score >= MIN_SIMILARITY
        ]

    def boosts(self, query: str, top_k: int = 5) -> Dict[Tuple[str, str], Dict]:
        """
        Map a query to the artists and genres that should be boosted.

        Keyed by (kind, name) — ("artist", "Fela Kuti") or ("genre", "afrobeat")
        — because a retrieved article describes an artist or a genre, not a
        song. Each entry carries the similarity and the source document, so an
        explanation can quote and cite what caused the boost.

        Where one name is reachable through several documents, the strongest
        similarity wins.
        """
        result: Dict[Tuple[str, str], Dict] = {}
        for document, score in self.search(query, top_k=top_k):
            for match in document.get("matches", []):
                key = (match["kind"], match["name"])
                if key not in result or score > result[key]["score"]:
                    result[key] = {"score": score, "document": document}
        return result


def summarise_document(document: Dict, max_chars: int = 180) -> str:
    """First sentence or so of an extract, for use inside an explanation."""
    text = " ".join(document["extract"].split())
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars]
    stop = cut.rfind(". ")
    return (cut[: stop + 1] if stop > 60 else cut.rstrip() + "…")


def _demo(query: str, index: Optional[CulturalIndex] = None) -> None:
    """Print what a query retrieves. Used by __main__ below."""
    index = index or CulturalIndex.from_file()
    print(f"\n=== query: {query!r} ===")
    hits = index.search(query)
    if not hits:
        print("  no document in the corpus matches this query")
        return
    for document, score in hits:
        names = ", ".join(
            f"{m['kind']}:{m['name']}" for m in document.get("matches", [])
        )
        print(f"  {score:.3f}  {document['wiki_title'][:34]:<34} -> {names}")
        print(f"         {summarise_document(document, 120)}")


if __name__ == "__main__":
    shared = CulturalIndex.from_file()
    print(f"indexed {len(shared.documents)} documents")
    for example in [
        "something political",
        "music for a wedding celebration",
        "sad songs about longing and exile",
        "traditional string instruments",
    ]:
        _demo(example, shared)
