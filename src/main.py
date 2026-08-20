"""
Command line runner for the music recommender.

Run from the project root with:

    python -m src.main
"""

from pathlib import Path

from src.pipeline import format_result, recommend
from src.recommender import load_songs

# Resolve data files relative to this file, not the shell's working directory,
# so the app runs the same way from anywhere.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SONGS_CSV = PROJECT_ROOT / "data" / "songs.csv"


def main() -> None:

    profiles = {
    "conflicting: metal + low energy": {"genre": "metal", "mood": "aggressive", "energy": 0.1},
    "out-of-range energy":             {"genre": "pop", "energy": 5.0},
    "typo + wrong case":               {"genre": "Pop", "mood": "saad"},
    "empty profile":                   {},
    "numeric-only mid values":         {"energy": 0.5, "valence": 0.5, "danceability": 0.5},
    "lofi but not acoustic":           {"genre": "lofi", "likes_acoustic": False},
    }

    songs = load_songs(str(SONGS_CSV))
    for name, prefs in profiles.items():
        print(f"\n=== {name}: {prefs} ===")
        result = recommend(prefs, songs=songs, k=5)
        print(format_result(result))

    

    # Starter example profile
    # user_prefs = {"genre": "pop", "mood": "happy", "energy": 0.8}

    # recommendations = recommend_songs(user_prefs, songs, k=5)

    # print("\nTop recommendations:\n")
    # for rec in recommendations:
    #     # You decide the structure of each returned item.
    #     # A common pattern is: (song, score, explanation)
    #     song, score, explanation = rec
    #     print(f"{song['title']} - Score: {score:.2f}")
    #     print(f"Because: {explanation}")
    #     print()


if __name__ == "__main__":
    main()
