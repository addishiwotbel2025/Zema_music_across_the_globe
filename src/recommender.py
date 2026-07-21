import csv
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

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

class Recommender:
    """
    OOP implementation of the recommendation logic.
    Required by tests/test_recommender.py
    """
    def __init__(self, songs: List[Song]):
        self.songs = songs

    '''
    function takes in only 1 song, scores and and also gives reasons for why it is scored that way
    '''
    def _score(self, user: UserProfile, song: Song) -> Tuple[float, List[str]]:
        """Score a Song against a UserProfile, returning (score, reasons)."""
        score = 0.0
        reasons: List[str] = []

        if song.genre == user.favorite_genre:
            score += GENRE_WEIGHT
            reasons.append(f"matches your favorite genre ({song.genre})")

        if song.mood == user.favorite_mood:
            score += MOOD_WEIGHT
            reasons.append(f"matches your favorite mood ({song.mood})")

        energy_fit = 1.0 - abs(user.target_energy - song.energy)
        score += ENERGY_WEIGHT * energy_fit
        if energy_fit > 0.8:
            reasons.append("energy is close to what you like")

        if user.target_valence is not None:
            valence_fit = 1.0 - abs(user.target_valence - song.valence)
            score += VALENCE_WEIGHT * valence_fit
            if valence_fit > 0.8:
                reasons.append("mood/positivity is a close match")

        if user.target_danceability is not None:
            dance_fit = 1.0 - abs(user.target_danceability - song.danceability)
            score += DANCEABILITY_WEIGHT * dance_fit
            if dance_fit > 0.8:
                reasons.append("danceability fits what you want")

        if user.likes_acoustic:
            score += ACOUSTIC_WEIGHT * song.acousticness
            if song.acousticness > 0.6:
                reasons.append("acoustic feel, which you enjoy")
        else:
            score += ACOUSTIC_WEIGHT * (1.0 - song.acousticness)

        # Additional signal: artist affinity.
        if user.favorite_artist and song.artist == user.favorite_artist:
            score += ARTIST_BONUS
            reasons.append(f"by an artist you like ({song.artist})")

        return score, reasons


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

'''
it converts songs.csv into a list of dicts 
like {"id": 1, "title": "Sunrise City", "artist": 
"Neon Echo", "genre": "pop", "energy": 0.82, ...}, 
with numbers stored as real numbers so score_song() 
can do arithmetic on them.
'''
def load_songs(csv_path: str) -> List[Dict]:
    """
    Loads songs from a CSV file.
    Required by src/main.py
    """
    numeric_fields = {
        "energy", "tempo_bpm", "valence", "danceability", "acousticness",
    }
    songs: List[Dict] = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            song: Dict = {}
            for key, value in row.items():
                if key == "id":
                    song[key] = int(value)
                elif key in numeric_fields:
                    song[key] = float(value)
                else:
                    song[key] = value
            songs.append(song)
    return songs

def score_song(user_prefs: Dict, song: Dict) -> Tuple[float, List[str]]:
    """
    Scores a single song against user preferences.
    Required by recommend_songs() and src/main.py

    user_prefs keys: "genre", "mood", "energy", and optionally "artist",
    "valence", "danceability", "likes_acoustic".
    """
    score = 0.0
    reasons: List[str] = []

    if user_prefs.get("genre") and song["genre"] == user_prefs["genre"]:
        score += GENRE_WEIGHT
        reasons.append(f"matches genre ({song['genre']})")

    if user_prefs.get("mood") and song["mood"] == user_prefs["mood"]:
        score += MOOD_WEIGHT
        reasons.append(f"matches mood ({song['mood']})")

    if "energy" in user_prefs:
        energy_fit = 1.0 - abs(user_prefs["energy"] - song["energy"])
        score += ENERGY_WEIGHT * energy_fit
        if energy_fit > 0.8:
            reasons.append("energy is a close match")

    if "valence" in user_prefs:
        valence_fit = 1.0 - abs(user_prefs["valence"] - song["valence"])
        score += VALENCE_WEIGHT * valence_fit
        if valence_fit > 0.8:
            reasons.append("mood/positivity is a close match")

    if "danceability" in user_prefs:
        dance_fit = 1.0 - abs(user_prefs["danceability"] - song["danceability"])
        score += DANCEABILITY_WEIGHT * dance_fit
        if dance_fit > 0.8:
            reasons.append("danceability is a close match")

    if "likes_acoustic" in user_prefs:
        if user_prefs["likes_acoustic"]:
            score += ACOUSTIC_WEIGHT * song["acousticness"]
            if song["acousticness"] > 0.6:
                reasons.append("acoustic feel, which you enjoy")
        else:
            score += ACOUSTIC_WEIGHT * (1.0 - song["acousticness"])

    # Additional signal: artist affinity.
    if user_prefs.get("artist") and song["artist"] == user_prefs["artist"]:
        score += ARTIST_BONUS
        reasons.append(f"by a preferred artist ({song['artist']})")

    return score, reasons

def recommend_songs(user_prefs: Dict, songs: List[Dict], k: int = 5) -> List[Tuple[Dict, float, str]]:
    """
    Functional implementation of the recommendation logic.
    Required by src/main.py
    """
    scored: List[Tuple[Dict, float, str]] = []
    for song in songs:
        score, reasons = score_song(user_prefs, song)
        explanation = "; ".join(reasons) if reasons else "general match"
        scored.append((song, score, explanation))

    scored.sort(key=lambda item: item[1], reverse=True)
    '''
    return the first 5 recommendations, or the first few recommendation
    based on user input.
    '''
    return scored[:k]
