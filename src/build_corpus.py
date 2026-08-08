"""
Build the cultural corpus that retrieval searches over.

Run from the project root:

    python -m src.build_corpus

Reads  data/songs.csv
Writes data/cultural_notes.jsonl
Caches data/raw/wiki_cache/     (gitignored)

One document per artist and per genre in the catalog, containing a Wikipedia
extract. This is the corpus retrieval searches, so its coverage decides which
songs the system can say anything cultural about.

Wikipedia rather than hand-written notes, for two reasons: the text is real
rather than generated, and every passage carries a URL, so a claim made in an
explanation can be traced back to a source. Content is CC BY-SA.

No API key is required or used. The endpoint is public; Wikimedia asks only
for a descriptive User-Agent.

Every response is cached to disk, so the network is contacted once per lookup
and never again. The recommender itself never makes a request at all: it reads
the finished .jsonl file.

Lookups escalate through a ladder rather than failing on the first miss:

    1. exact      the name as it appears in the catalog
    2. variant    title-cased, or with " music" appended for genres
    3. search     Wikipedia's search API, taking the top result
    4. miss       recorded explicitly, never silently skipped

Each document records which rung produced it, because a note found by
full-text search is a weaker match than an exact title hit and should not look
equally authoritative later.
"""

import csv
import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SONGS_CSV = PROJECT_ROOT / "data" / "songs.csv"
OUT_JSONL = PROJECT_ROOT / "data" / "cultural_notes.jsonl"
CACHE_DIR = PROJECT_ROOT / "data" / "raw" / "wiki_cache"

WIKI_API = "https://en.wikipedia.org/w/api.php"

# Article titles too generic to be a real answer for anything. Wikipedia's
# search will happily return "Music genre" for a query like "french music
# genre", and a confidently wrong document is worse than a missing one: it
# retrieves just as well and says nothing true about the song.
GENERIC_TITLES = {
    "music genre", "music", "genre", "list of music genres",
    "list of music genres and styles", "list of musical genres",
    "popular music", "world music", "folk music", "music industry",
    "music of the world", "cultural music",
}

# Wikimedia policy asks for a descriptive User-Agent with a way to make
# contact. Replace the URL below with your own repository or email address.
USER_AGENT = (
    "MusicRecommenderCourseProject/1.0 "
    "(https://github.com/codepath/applied-ai-system-project; educational use) "
    "python-urllib"
)

# Only applied to requests that actually reach the network; cache hits are free.
REQUEST_DELAY_SECONDS = 0.2

# Low enough to keep real one-sentence leads. An earlier threshold of 120
# silently discarded Mulatu Astatke ("...considered the father of Ethio-jazz",
# 91 characters) — the only Ethiopian artist in the catalog — for being short.
MIN_EXTRACT_CHARS = 40


def _cache_path(url: str) -> Path:
    """A stable filename per URL. Hashed because titles contain '/' and '?'."""
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]
    return CACHE_DIR / f"{digest}.json"


def _get_json(url: str) -> Optional[Dict]:
    """
    GET a URL and parse JSON, using the on-disk cache when possible.

    Failures are cached too, as `null`. Without that, every re-run would retry
    every miss, which is most of the request volume once the hits are cached.
    """
    path = _cache_path(url)
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass  # Corrupt cache entry: fall through and re-fetch.

    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    payload: Optional[Dict]
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.HTTPError, urllib.error.URLError,
            json.JSONDecodeError, TimeoutError, OSError):
        payload = None
    time.sleep(REQUEST_DELAY_SECONDS)

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return payload


def fetch_summary(title: str) -> Optional[Dict]:
    """
    Fetch an article's full intro section.

    Uses `prop=extracts` rather than the REST summary endpoint: the summary
    returns one or two sentences, which is too thin to retrieve against. A
    query like "something political" cannot match text that never gets past
    "Nigerian musician". The intro section runs to several paragraphs.
    """
    params = urllib.parse.urlencode({
        "action": "query", "prop": "extracts|info|pageprops", "exintro": 1,
        "explaintext": 1, "inprop": "url", "redirects": 1,
        "titles": title, "format": "json",
    })
    data = _get_json(f"{WIKI_API}?{params}")
    pages = (data or {}).get("query", {}).get("pages", {})
    for page_id, page in pages.items():
        if page_id == "-1" or "missing" in page:
            return None
        # A disambiguation page is a menu of links, not an article. Ask the API
        # rather than pattern-matching the prose: the wording varies more than
        # it appears ("Spanish might refer to", "Salsa most often refers to"),
        # and guessing at phrasing let the article about the sauce into the
        # corpus as the cultural note for salsa music.
        if "disambiguation" in page.get("pageprops", {}):
            return None
        extract = (page.get("extract") or "").strip()
        # Name-index pages are not flagged as disambiguation but are just as
        # useless: "Alonzo is both a given name and a Spanish surname. Notable
        # people with the name include:" was being cited as the cultural note
        # for a French rapper.
        lowered = extract.lower()
        if "notable people with the" in lowered or lowered.endswith("include:"):
            return None
        if len(extract) < MIN_EXTRACT_CHARS:
            return None
        if page.get("title", "").strip().lower() in GENERIC_TITLES:
            return None
        return {
            "wiki_title": page.get("title", title),
            "extract": extract,
            "url": page.get("fullurl", ""),
        }
    return None


def search_title(query: str) -> Optional[str]:
    """
    Ask Wikipedia's search API for the best-matching article title.

    Generic results are rejected rather than accepted as a weak answer.
    """
    params = urllib.parse.urlencode({
        "action": "query", "list": "search", "srsearch": query,
        "srlimit": 3, "format": "json",
    })
    data = _get_json(f"{WIKI_API}?{params}")
    for result in (data or {}).get("query", {}).get("search", []):
        title = result.get("title", "")
        if title.strip().lower() not in GENERIC_TITLES:
            return title
    return None


def candidate_titles(name: str, kind: str) -> List[Tuple[str, str]]:
    """(strategy, title) pairs to try, in escalating order."""
    candidates = [("exact", name), ("variant", name.title())]
    if kind == "genre":
        # Genre names here are lowercase and often need a qualifier: the
        # article "Morna" is about a bird, "Morna (music)" is the Cape Verdean
        # genre.
        candidates.append(("variant", f"{name.title()} music"))
    return candidates


def lookup(name: str, kind: str) -> Optional[Dict]:
    """Walk the escalation ladder until something yields a usable extract."""
    for strategy, title in candidate_titles(name, kind):
        found = fetch_summary(title)
        if found:
            return {**found, "strategy": strategy}

    # "french music genre" matches the article *Music genre*. "french music"
    # matches *Music of France*, which is what was actually wanted.
    query = name if kind == "artist" else f"{name} music"
    searched = search_title(query)
    if searched:
        found = fetch_summary(searched)
        if found:
            return {**found, "strategy": "search"}
    return None


def collect_targets() -> Tuple[List[str], List[str]]:
    """Unique artists and genres in the catalog, in stable order."""
    artists: Dict[str, None] = {}
    genres: Dict[str, None] = {}
    with open(SONGS_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            artists.setdefault(row["artist"], None)
            genres.setdefault(row["genre"], None)
    return list(artists), list(genres)


def main() -> None:
    if not SONGS_CSV.exists():
        raise SystemExit(f"Missing {SONGS_CSV}. Run: python -m src.build_catalog")

    artists, genres = collect_targets()
    targets = ([(name, "artist") for name in artists] +
               [(name, "genre") for name in genres])
    print(f"looking up {len(artists)} artists and {len(genres)} genres "
          f"({len(targets)} documents)")
    print(f"cache: {CACHE_DIR.relative_to(PROJECT_ROOT)}\n")

    # Keyed by Wikipedia title, not by catalog name. Several catalog names can
    # resolve to the same article ("turkish" and "turkish pop" both land on
    # *Music of Turkey*), and storing that text twice would distort the inverse
    # document frequencies that make TF-IDF ranking work. One article, one
    # document, with every name it covers recorded on it.
    documents: Dict[str, Dict] = {}
    misses: List[Tuple[str, str]] = []
    by_strategy: Dict[str, int] = {}
    merged = 0

    for index, (name, kind) in enumerate(targets, start=1):
        found = lookup(name, kind)
        label = f"[{index:>3}/{len(targets)}] {kind:<6} {name[:32]:<32}"
        if found is None:
            misses.append((name, kind))
            print(f"{label} MISS")
            continue

        title = found["wiki_title"]
        existing = documents.get(title)
        if existing is not None:
            existing["matches"].append({"kind": kind, "name": name})
            merged += 1
            print(f"{label} merged   {title[:28]}")
            continue

        by_strategy[found["strategy"]] = by_strategy.get(found["strategy"], 0) + 1
        documents[title] = {
            "doc_id": f"wiki:{title}",
            "wiki_title": title,
            "url": found["url"],
            "extract": found["extract"],
            "strategy": found["strategy"],
            "matches": [{"kind": kind, "name": name}],
        }
        print(f"{label} {found['strategy']:<8} {title[:28]}")

    with open(OUT_JSONL, "w", encoding="utf-8") as f:
        for doc in documents.values():
            f.write(json.dumps(doc, ensure_ascii=False) + "\n")

    print(f"\nwrote {len(documents)} documents to "
          f"{OUT_JSONL.relative_to(PROJECT_ROOT)}")
    for strategy, count in sorted(by_strategy.items()):
        print(f"  found by {strategy:<8} {count}")
    if merged:
        print(f"  merged into an existing article  {merged}")

    # Misses are reported rather than swallowed. Uneven Wikipedia coverage is a
    # stated limitation of this system, so the gaps have to stay visible.
    if misses:
        print(f"\nno article found ({len(misses)}):")
        for name, kind in misses:
            print(f"  - {kind:<6} {name}")


if __name__ == "__main__":
    main()
