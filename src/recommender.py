"""
Content-based music recommender.

Scoring lives in one place: `_score_features`. The two public entry points are
thin adapters over it, so the dataclass API (`Recommender`) and the dict API
(`score_song` / `recommend_songs`) can never drift apart.
"""

import csv
from dataclasses import asdict, dataclass
from typing import Dict, List, Optional, Tuple

# --- Scoring weights -------------------------------------------------------
# Genre is the broadest taste signal, so it leads; mood and energy refine
# within a genre; acoustic fit and artist affinity are tie-breakers. Artist
# is deliberately small: it's a sparse signal in this dataset, so it should
# nudge ties without overpowering the core taste match.
GENRE_WEIGHT = 3.0
MOOD_WEIGHT = 2.0
ENERGY_WEIGHT = 2.0
VALENCE_WEIGHT = 1.5
DANCEABILITY_WEIGHT = 1.5
ACOUSTIC_WEIGHT = 1.0
ARTIST_BONUS = 1.0

# The same weights keyed by feature name. Callers can pass a modified copy to
# re-prioritise features per user without touching the scoring logic.
DEFAULT_WEIGHTS: Dict[str, float] = {
    "genre": GENRE_WEIGHT,
    "mood": MOOD_WEIGHT,
    "energy": ENERGY_WEIGHT,
    "valence": VALENCE_WEIGHT,
    "danceability": DANCEABILITY_WEIGHT,
    "acousticness": ACOUSTIC_WEIGHT,
    "artist": ARTIST_BONUS,
}

# Features scored by closeness between a user's target and the song's value.
_PROXIMITY_FEATURES = ("energy", "valence", "danceability")

_PROXIMITY_REASONS = {
    "energy": "energy is close to what you like",
    "valence": "mood/positivity is a close match",
    "danceability": "danceability fits what you want",
}


@dataclass
class Song:
    """
    Represents a song and its attributes.
    Required by tests/test_recommender.py
    """
    id: int
    title: str
    artist: str
    genre: str
    mood: str
    energy: float
    tempo_bpm: float
    valence: float
    danceability: float
    acousticness: float


@dataclass
class UserProfile:
    """
    Represents a user's taste preferences.
    Required by tests/test_recommender.py
    """
    favorite_genre: str
    favorite_mood: str
    target_energy: float
    likes_acoustic: bool
    # Optional taste dimensions. Each defaults to None so a profile can ignore
    # it entirely (and existing callers/tests that omit it keep working); the
    # matching term only contributes to the score when the field is set.
    favorite_artist: Optional[str] = None
    target_valence: Optional[float] = None
    target_danceability: Optional[float] = None

    def to_prefs(self) -> Dict:
        """Convert to the dict form `score_song` expects, dropping unset fields."""
        prefs: Dict = {
            "genre": self.favorite_genre,
            "mood": self.favorite_mood,
            "energy": self.target_energy,
            "likes_acoustic": self.likes_acoustic,
        }
        if self.favorite_artist is not None:
            prefs["artist"] = self.favorite_artist
        if self.target_valence is not None:
            prefs["valence"] = self.target_valence
        if self.target_danceability is not None:
            prefs["danceability"] = self.target_danceability
        return prefs


def _score_features(
    prefs: Dict,
    song: Dict,
    weights: Optional[Dict[str, float]] = None,
) -> Tuple[float, List[str]]:
    """
    The single scoring implementation.

    `prefs` and `song` are both plain dicts. A preference that is absent
    contributes nothing, so partial profiles are valid input. `weights`
    overrides DEFAULT_WEIGHTS per feature, which is how per-user feature
    prioritisation is applied.
    """
    w = weights if weights is not None else DEFAULT_WEIGHTS
    score = 0.0
    reasons: List[str] = []

    # Exact-match features.
    if prefs.get("genre") and song["genre"] == prefs["genre"]:
        score += w.get("genre", 0.0)
        reasons.append(f"matches your favorite genre ({song['genre']})")

    if prefs.get("mood") and song["mood"] == prefs["mood"]:
        score += w.get("mood", 0.0)
        reasons.append(f"matches your favorite mood ({song['mood']})")

    # Proximity features: closer to the user's target scores higher.
    for feature in _PROXIMITY_FEATURES:
        if prefs.get(feature) is None:
            continue
        fit = 1.0 - abs(prefs[feature] - song[feature])
        score += w.get(feature, 0.0) * fit
        if fit > 0.8:
            reasons.append(_PROXIMITY_REASONS[feature])

    # Acoustic fit is directional: liking acoustic rewards high acousticness,
    # and not liking it rewards the inverse.
    if "likes_acoustic" in prefs:
        acoustic_weight = w.get("acousticness", 0.0)
        if prefs["likes_acoustic"]:
            score += acoustic_weight * song["acousticness"]
            if song["acousticness"] > 0.6:
                reasons.append("acoustic feel, which you enjoy")
        else:
            score += acoustic_weight * (1.0 - song["acousticness"])

    # Additional signal: artist affinity.
    if prefs.get("artist") and song["artist"] == prefs["artist"]:
        score += w.get("artist", 0.0)
        reasons.append(f"by an artist you like ({song['artist']})")

    return score, reasons


class Recommender:
    """
    OOP implementation of the recommendation logic.
    Required by tests/test_recommender.py
    """

    def __init__(self, songs: List[Song], weights: Optional[Dict[str, float]] = None):
        self.songs = songs
        self.weights = weights

    '''
    function takes in only 1 song, scores and and also gives reasons for why it is scored that way
    '''
    def _score(self, user: UserProfile, song: Song) -> Tuple[float, List[str]]:
        """Score a Song against a UserProfile, returning (score, reasons)."""
        return _score_features(user.to_prefs(), asdict(song), self.weights)

    def recommend(self, user: UserProfile, k: int = 5) -> List[Song]:
        """Return the top-k songs for a user, ranked by score (highest first)."""
        ranked = sorted(
            self.songs,
            key=lambda s: self._score(user, s)[0],
            reverse=True,
        )
        return ranked[:k]

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        """Return a human-readable sentence explaining why a song was recommended."""
        _, reasons = self._score(user, song)
        if not reasons:
            return "A reasonable match based on your overall preferences."
        return "Recommended because it " + ", and ".join(reasons) + "."


NUMERIC_FIELDS = frozenset(
    {"energy", "tempo_bpm", "valence", "danceability", "acousticness"}
)


'''
it converts songs.csv into a list of dicts
like {"id": 1, "title": "Sunrise City", "artist":
"Neon Echo", "genre": "pop", "energy": 0.82, ...},
with numbers stored as real numbers so score_song()
can do arithmetic on them.
'''
def load_songs(csv_path: str) -> List[Dict]:
    """
    Loads songs from a CSV file into a list of dicts, with numeric columns
    parsed as floats so scoring can do arithmetic on them.
    Required by src/main.py
    """
    songs: List[Dict] = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            song: Dict = {}
            for key, value in row.items():
                if key == "id":
                    song[key] = int(value)
                elif key in NUMERIC_FIELDS:
                    song[key] = float(value)
                else:
                    song[key] = value
            songs.append(song)
    return songs


def score_song(
    user_prefs: Dict,
    song: Dict,
    weights: Optional[Dict[str, float]] = None,
) -> Tuple[float, List[str]]:
    """
    Scores a single song against user preferences.
    Required by recommend_songs() and src/main.py

    user_prefs keys: "genre", "mood", "energy", and optionally "artist",
    "valence", "danceability", "likes_acoustic".
    """
    return _score_features(user_prefs, song, weights)


def recommend_songs(
    user_prefs: Dict,
    songs: List[Dict],
    k: int = 5,
    weights: Optional[Dict[str, float]] = None,
) -> List[Tuple[Dict, float, str]]:
    """
    Functional implementation of the recommendation logic. Returns the top-k
    (song, score, explanation) tuples, highest score first.
    Required by src/main.py
    """
    scored: List[Tuple[Dict, float, str]] = []
    for song in songs:
        score, reasons = score_song(user_prefs, song, weights)
        explanation = "; ".join(reasons) if reasons else "general match"
        scored.append((song, score, explanation))

    scored.sort(key=lambda item: item[1], reverse=True)
    '''
    return the first 5 recommendations, or the first few recommendation
    based on user input.
    '''
    return scored[:k]
