# 🎵 Music Recommender Simulation

## Project Summary

In this project you will build and explain a small music recommender system.

Your goal is to:

- Represent songs and a user "taste profile" as data
- Design a scoring rule that turns that data into recommendations
- Evaluate what your system gets right and wrong
- Reflect on how this mirrors real world AI recommenders

Replace this paragraph with your own summary of what your version does.

---

## How The System Works

Explain your design in plain language.

Some prompts to answer:

- What features does each `Song` use in your system
    it uses [energy, valence, danceability, acousticness, tempo_normalized]
- What information does your `UserProfile` store
    favorite_genre
    favorite_mood
    target_energy
    likes_acoustic
    favorite_artist
- How does your `Recommender` compute a score for each song
  GENRE_WEIGHT = 3.0
  MOOD_WEIGHT = 2.0
  ENERGY_WEIGHT = 2.0
  ACOUSTIC_WEIGHT = 1.0
  ARTIST_BONUS = 1.0
- How do you choose which songs to recommend
  it will be based on ranking. all the scores based on the music characteristics will be added and the ones with higher scores will be recommended.
You can include a simple diagram or bullet list if helpful.

---

## Getting Started

### Setup

1. Create a virtual environment (optional but recommended):

   ```bash
   python -m venv .venv
   source .venv/bin/activate      # Mac or Linux
   .venv\Scripts\activate         # Windows

2. Install dependencies

```bash
pip install -r requirements.txt
```

3. Run the app:

```bash
python -m src.main
```

### Running Tests

Run the starter tests with:

```bash
pytest
```

You can add more tests in `tests/test_recommender.py`.

---

## Sample Recommendation Output

Paste a sample of your recommender's output here as a text block so a reader can see what it produces:

```
Top recommendations:

Sunrise City - Score: 6.96
Because: matches genre (pop); matches mood (happy); energy is a close match

Gym Hero - Score: 4.74
Because: matches genre (pop); energy is a close match

Rooftop Lights - Score: 3.92
Because: matches mood (happy); energy is a close match

Concrete Dreams - Score: 1.96
Because: energy is a close match

Night Drive Loop - Score: 1.90
Because: energy is a close match
```

**Screenshot or video** *(optional)*: <!-- Insert a screenshot or demo video link here -->

---

## Experiments You Tried

Use this section to document the experiments you ran. For example:

- What happened when you changed the weight on genre from 2.0 to 0.5
- What happened when you added tempo or valence to the score
- How did your system behave for different types of users

---

## Limitations and Risks

Summarize some limitations of your recommender.

Examples:

- It only works on a tiny catalog
- It does not understand lyrics or language
- It might over favor one genre or mood

You will go deeper on this in your model card.

---

## Reflection

Read and complete `model_card.md`:

[**Model Card**](model_card.md)

Write 1 to 2 paragraphs here about what you learned:

- about how recommenders turn data into predictions
- about where bias or unfairness could show up in systems like this



