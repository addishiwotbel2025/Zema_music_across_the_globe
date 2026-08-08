"""
Build the song catalog from the raw Spotify-derived dataset.

Run from the project root:

    python -m src.build_catalog

Reads  data/raw/dataset.csv   (19MB, gitignored, downloaded separately)
Writes data/songs.csv         (the catalog the recommender actually uses)

Why this is a script and not a hand-written CSV: the selection and cleaning
rules are the interesting part, and they need to be inspectable and re-runnable.

Selection uses two paths, and every output row records which one produced it:

  genre-label      Taken from a genre label that was checked by hand and found
                   to contain what it claims.
  artist-allowlist Taken by artist name, ignoring the dataset's genre label
                   entirely, with genre and region assigned here.

The second path exists because the dataset's labels are unreliable: `afrobeat`
is led by a Puerto Rican rap group, `world-music` is worship pop, and `reggae`
returns Bad Bunny. The music is mis-filed rather than missing, so it is
recovered by name. See model_card.md section 6b.
"""

import csv
from pathlib import Path
from typing import Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_CSV = PROJECT_ROOT / "data" / "raw" / "dataset.csv"
OUT_CSV = PROJECT_ROOT / "data" / "songs.csv"

MAX_PER_ARTIST = 3
MAX_PER_GENRE = 6

# --- Path 1: genre labels verified by inspection ---------------------------
# Each was checked by reading its top tracks. Labels that failed that check
# (afrobeat, reggae, world-music, ska, dub, brazil, pagode, iranian, latin,
# latino) are deliberately absent.
VERIFIED_GENRES: Dict[str, str] = {
    "tango": "Argentina",
    "salsa": "Latin America",
    "samba": "Brazil",
    "mpb": "Brazil",
    "reggaeton": "Puerto Rico",
    "spanish": "Spain",
    "french": "France",
    "swedish": "Sweden",
    "turkish": "Turkey",
    "indian": "India",
    "j-pop": "Japan",
    "k-pop": "South Korea",
    "mandopop": "Taiwan",
    "cantopop": "Hong Kong",
}

# --- Path 2: artists selected by name, label ignored -----------------------
# (genre, region) assigned by hand. This is a human judgement call and is
# recorded as such in the model card: it substitutes one curator's bias for
# the platform's, and it does not scale beyond a list a person can check.
ARTIST_ALLOWLIST: Dict[str, tuple] = {
    # West Africa
    "Fela Kuti": ("afrobeat", "Nigeria"),
    "Burna Boy": ("afrobeats", "Nigeria"),
    "Wizkid": ("afrobeats", "Nigeria"),
    "Rema": ("afrobeats", "Nigeria"),
    "Tems": ("afrobeats", "Nigeria"),
    "Tiwa Savage": ("afrobeats", "Nigeria"),
    "Ali Farka Touré": ("desert blues", "Mali"),
    "Toumani Diabaté": ("kora", "Mali"),
    "Tinariwen": ("tuareg rock", "Mali"),
    "Salif Keita": ("mande", "Mali"),
    "Amadou & Mariam": ("mande", "Mali"),
    # Horn of Africa
    "Mulatu Astatke": ("ethio-jazz", "Ethiopia"),
    # Southern Africa
    "Hugh Masekela": ("south african jazz", "South Africa"),
    "Ladysmith Black Mambazo": ("isicathamiya", "South Africa"),
    "Master KG": ("south african house", "South Africa"),
    "Black Coffee": ("south african house", "South Africa"),
    # Jamaica
    "Bob Marley & The Wailers": ("reggae", "Jamaica"),
    "Peter Tosh": ("reggae", "Jamaica"),
    "Jimmy Cliff": ("reggae", "Jamaica"),
    "Burning Spear": ("roots reggae", "Jamaica"),
    "Gregory Isaacs": ("lovers rock", "Jamaica"),
    "Toots & The Maytals": ("ska", "Jamaica"),
    "Sister Nancy": ("dancehall", "Jamaica"),
    "Chronixx": ("reggae revival", "Jamaica"),
    # Atlantic islands
    "Cesária Evora": ("morna", "Cape Verde"),
    # Greece
    "Mikis Theodorakis": ("greek folk", "Greece"),
    "George Dalaras": ("laiko", "Greece"),
    # Turkey, traditional and Anatolian rock
    "Barış Manço": ("anatolian rock", "Turkey"),
    "Selda Bağcan": ("anatolian rock", "Turkey"),
    "Sezen Aksu": ("turkish pop", "Turkey"),
    "Neşet Ertaş": ("turkish folk", "Turkey"),
    # Iberia
    "Paco de Lucía": ("flamenco", "Spain"),
    # Central Asia
    "The HU": ("mongolian folk metal", "Mongolia"),
}


def derive_mood(valence: float, energy: float) -> str:
    """
    Derive a mood from valence and energy.

    The source data has no mood column, so this mapping is an invention of this
    project. Only four moods, because two numbers cannot honestly support more.
    Emotional categories also do not translate cleanly between musical
    traditions; see model_card.md section 6b.
    """
    if valence >= 0.5:
        return "celebratory" if energy >= 0.6 else "warm"
    return "intense" if energy >= 0.6 else "melancholic"


def clean_row(row: Dict) -> Optional[Dict]:
    """
    Return the row's numeric fields parsed, or None if the row is unusable.

    Rejects the mechanical defects found while profiling: unparseable numbers,
    a tempo of zero (not a possible tempo), and missing core text fields.
    """
    for field in ("artists", "track_name"):
        if not row.get(field, "").strip():
            return None
    try:
        values = {
            "energy": float(row["energy"]),
            "valence": float(row["valence"]),
            "danceability": float(row["danceability"]),
            "acousticness": float(row["acousticness"]),
            "tempo_bpm": float(row["tempo"]),
            "popularity": int(row["popularity"]),
        }
    except (ValueError, KeyError, TypeError):
        return None
    if values["tempo_bpm"] <= 0:
        return None
    return values


def primary_artist(artists_field: str) -> str:
    """The first name in a semicolon-separated artist credit."""
    return artists_field.split(";")[0].strip()


def match_allowlist(artists_field: str) -> Optional[str]:
    """
    Return the allowlisted artist if they are the *primary* credit.

    Two rules, each fixing a way this quietly goes wrong:

    Exact, not substring. A substring search pairs "The HU" with "The Human
    League".

    Primary, not merely present. "Sete" is credited to
    "BLOND:ISH;Francis Mercier;Amadou & Mariam" — a house track with Malian
    guests. Accepting any credited artist files it as Malian mande, which is
    the same mislabelling this catalog exists to avoid. Requiring the primary
    credit also drops "One Dance" (a Drake track that mentions Wizkid) while
    keeping "Calm Down" and "Jerusalema", where the allowlisted artist leads.
    """
    primary = primary_artist(artists_field)
    return primary if primary in ARTIST_ALLOWLIST else None


def load_candidates() -> tuple:
    """Single pass over the raw file, collecting both selection paths."""
    by_genre: Dict[str, List[Dict]] = {g: [] for g in VERIFIED_GENRES}
    by_artist: Dict[str, List[Dict]] = {a: [] for a in ARTIST_ALLOWLIST}
    seen_track_ids = set()
    seen_songs = set()

    with open(RAW_CSV, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            # 21.3% of rows are duplicates by track_id, because tracks appear
            # under several genre labels. Keep the first sighting only.
            track_id = row.get("track_id", "")
            if track_id in seen_track_ids:
                continue

            values = clean_row(row)
            if values is None:
                continue

            # track_id alone is not enough: the same song is re-released and
            # remastered under different ids, which put Barış Manço's
            # "Kol Düğmeleri" into the catalog twice.
            song_key = (row["track_name"].strip().lower(),
                        primary_artist(row["artists"]).lower())
            if song_key in seen_songs:
                continue

            seen_track_ids.add(track_id)
            seen_songs.add(song_key)

            record = {
                "title": row["track_name"].strip(),
                "artist": primary_artist(row["artists"]),
                **values,
            }

            # Artist selection wins over genre selection: it carries a
            # hand-checked label, which the genre path does not.
            allowlisted = match_allowlist(row["artists"])
            if allowlisted is not None:
                genre, region = ARTIST_ALLOWLIST[allowlisted]
                by_artist[allowlisted].append(
                    {**record, "genre": genre, "region": region,
                     "source": "artist-allowlist"}
                )
                continue

            label = row.get("track_genre", "")
            if label in by_genre:
                by_genre[label].append(
                    {**record, "genre": label, "region": VERIFIED_GENRES[label],
                     "source": "genre-label"}
                )

    return by_genre, by_artist


def select(by_genre: Dict, by_artist: Dict) -> List[Dict]:
    """Take the most popular tracks from each bucket, subject to the caps."""
    chosen: List[Dict] = []

    for artist, rows in sorted(by_artist.items()):
        rows.sort(key=lambda r: r["popularity"], reverse=True)
        chosen.extend(rows[:MAX_PER_ARTIST])

    for label, rows in sorted(by_genre.items()):
        rows.sort(key=lambda r: r["popularity"], reverse=True)
        per_artist: Dict[str, int] = {}
        taken = 0
        for row in rows:
            if taken >= MAX_PER_GENRE:
                break
            # Cap per artist inside a genre too, so one act cannot fill a label.
            count = per_artist.get(row["artist"], 0)
            if count >= 2:
                continue
            per_artist[row["artist"]] = count + 1
            chosen.append(row)
            taken += 1

    return chosen


def write_catalog(rows: List[Dict]) -> None:
    """Write the catalog, assigning stable ids in output order."""
    columns = ["id", "title", "artist", "genre", "mood", "energy", "tempo_bpm",
               "valence", "danceability", "acousticness", "region", "source"]

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for index, row in enumerate(rows, start=1):
            writer.writerow({
                "id": index,
                "title": row["title"],
                "artist": row["artist"],
                "genre": row["genre"],
                "mood": derive_mood(row["valence"], row["energy"]),
                "energy": f"{row['energy']:.2f}",
                "tempo_bpm": f"{row['tempo_bpm']:.0f}",
                "valence": f"{row['valence']:.2f}",
                "danceability": f"{row['danceability']:.2f}",
                "acousticness": f"{row['acousticness']:.2f}",
                "region": row["region"],
                "source": row["source"],
            })


def main() -> None:
    if not RAW_CSV.exists():
        raise SystemExit(
            f"Missing {RAW_CSV}.\nDownload it first:\n"
            "  mkdir -p data/raw && curl -sSL -o data/raw/dataset.csv \\\n"
            "    https://huggingface.co/datasets/maharshipandya/"
            "spotify-tracks-dataset/resolve/main/dataset.csv"
        )

    by_genre, by_artist = load_candidates()
    rows = select(by_genre, by_artist)
    write_catalog(rows)

    # Report what the selection actually produced, including what it missed.
    # An artist in the allowlist that yielded nothing is a real finding, not a
    # silent no-op, so it is printed rather than swallowed.
    missing = sorted(a for a, r in by_artist.items() if not r)
    regions = sorted({r["region"] for r in rows})
    by_source: Dict[str, int] = {}
    for row in rows:
        by_source[row["source"]] = by_source.get(row["source"], 0) + 1

    print(f"wrote {len(rows)} songs to {OUT_CSV.relative_to(PROJECT_ROOT)}")
    for source, count in sorted(by_source.items()):
        print(f"  {source:<18} {count}")
    print(f"  regions            {len(regions)}")
    if missing:
        print(f"\nallowlisted artists with no tracks found ({len(missing)}):")
        for name in missing:
            print(f"  - {name}")


if __name__ == "__main__":
    main()
