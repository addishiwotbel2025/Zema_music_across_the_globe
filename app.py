"""
Streamlit demo for the music recommender.

Run from the project root with:

    streamlit run app.py

This is a thin UI over src/pipeline.py — it doesn't reimplement any
scoring, retrieval, or guardrail logic, it just calls recommend() and
displays what comes back, including the guardrail disclosures and
retrieval citations.
"""

import streamlit as st
import streamlit.components.v1 as components

from src.guardrails import _known_values
from src.pipeline import recommend
from src.recommender import DEFAULT_WEIGHTS, load_songs
from src.retrieval import CulturalIndex

st.set_page_config(page_title="Music Recommender", page_icon="🎵")


@st.cache_resource
def load_data():
    songs = load_songs("data/songs.csv")
    index = CulturalIndex.from_file()
    return songs, index


songs, index = load_data()
genres = sorted(_known_values(songs, "genre"))
moods = sorted(_known_values(songs, "mood"))

st.title("🎵 Music Recommender")
st.caption(
    "Content-based scoring + RAG over a Wikipedia cultural corpus, "
    "with guardrails on the input."
)

with st.form("prefs_form"):
    col1, col2 = st.columns(2)
    with col1:
        genre = st.selectbox("Favorite genre", ["(none)"] + genres)
        mood = st.selectbox("Favorite mood", ["(none)"] + moods)
        artist = st.text_input("Favorite artist (optional)")
    with col2:
        energy = st.slider("Target energy", 0.0, 1.0, 0.5)
        valence = st.slider("Target valence (mood positivity)", 0.0, 1.0, 0.5)
        danceability = st.slider("Target danceability", 0.0, 1.0, 0.5)
        likes_acoustic = st.checkbox("Likes acoustic songs")

    context_query = st.text_input(
        "Cultural / context query (optional)",
        placeholder='e.g. "ethiopian jazz" or "music about activism"',
    )
    priorities = st.multiselect(
        "Prioritize these features (optional)", sorted(DEFAULT_WEIGHTS),
    )
    k = st.number_input("How many recommendations?", min_value=1, max_value=20, value=5)

    submitted = st.form_submit_button("Get Recommendations")

if submitted:
    prefs = {
        "energy": energy,
        "valence": valence,
        "danceability": danceability,
        "likes_acoustic": likes_acoustic,
    }
    if genre != "(none)":
        prefs["genre"] = genre
    if mood != "(none)":
        prefs["mood"] = mood
    if artist.strip():
        prefs["artist"] = artist.strip()

    result = recommend(
        prefs, context_query or None, k=int(k),
        priorities=priorities or None, songs=songs, index=index,
    )

    if result["guardrail_issues"]:
        st.warning("**Guardrails:**\n\n" + "\n\n".join(
            f"- {issue}" for issue in result["guardrail_issues"]
        ))

    if result["strategy"] == "diverse_sample":
        st.info("No usable preferences — showing a diverse sample, not a ranking.")

    if result["retrieval_used"]:
        if result["retrieved"]:
            st.subheader("Retrieved from the cultural corpus")
            for hit in result["retrieved"]:
                st.write(f"`{hit['score']:.3f}`  {hit['title']}")
        else:
            st.caption("Retrieval found nothing above the similarity threshold.")

    st.subheader("Recommendations")
    for position, item in enumerate(result["recommendations"], start=1):
        song = item["song"]
        with st.container(border=True):
            st.markdown(f"**{position}. {song['title']}** — {song['artist']}")
            st.caption(
                f"{song['genre']} · {song['region']} · {song['mood']} · "
                f"score {item['score']:.2f}"
            )
            if song.get("track_id"):
                components.iframe(
                    f"https://open.spotify.com/embed/track/{song['track_id']}"
                    "?utm_source=generator&theme=0",
                    height=80,
                )
            else:
                st.caption("No Spotify preview available for this track.")
            if item["citation"]:
                citation = item["citation"]
                st.markdown(
                    f"🌍 *Cultural note ({citation['similarity']:.3f})* "
                    f"— [{citation['title']}]({citation['url']})"
                )
                st.markdown(f"> {citation['quote']}")
