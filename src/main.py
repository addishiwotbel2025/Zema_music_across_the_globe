"""
Command line runner for the Music Recommender Simulation.

This file helps you quickly run and test your recommender.

You will implement the functions in recommender.py:
- load_songs
- score_song
- recommend_songs
"""

from recommender import load_songs, recommend_songs


def main() -> None:

    profiles = {
    "conflicting: metal + low energy": {"genre": "metal", "mood": "aggressive", "energy": 0.1},
    "out-of-range energy":             {"genre": "pop", "energy": 5.0},
    "typo + wrong case":               {"genre": "Pop", "mood": "saad"},
    "empty profile":                   {},
    "numeric-only mid values":         {"energy": 0.5, "valence": 0.5, "danceability": 0.5},
    "lofi but not acoustic":           {"genre": "lofi", "likes_acoustic": False},
    }

    songs = load_songs("data/songs.csv") 
    for name, prefs in profiles.items():
        print(f"\n=== {name}: {prefs} ===")
        for song, score, explanation in recommend_songs(prefs, songs, k=5):
            print(f"{song['title']} - Score: {score:.2f}  ({explanation})")

    

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
