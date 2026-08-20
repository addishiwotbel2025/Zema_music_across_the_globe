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
## Guardrail Examples: Before and After

I ran the same six weird/broken inputs through the system twice — once before I built the guardrails, once after — so you can see exactly what changed.

Here's what each one is testing, in plain words:

- **conflicting: metal + low energy** — a genre/mood combo that doesn't really exist in the catalog. This one wasn't broken before, it's just a normal "nothing matches well" case.
- **out-of-range energy** — I asked for `energy: 5.0`, but energy is only supposed to go from 0 to 1. Before the fix, this made every single score negative and made no sense. Now it just gets capped back down to 1.0 automatically, so the scores stay sane.
- **typo + wrong case** — I typed `"Pop"` with a capital letter and `"saad"` instead of a real mood. Before, both of these silently matched nothing and every song scored a flat `0.00`, but it still looked like a real ranked list. Now the system tells you it couldn't recognize either value, and since nothing usable was left, it honestly says "here's a random spread of songs" instead of pretending to rank them.
- **empty profile** — I gave it literally no preferences at all. Before, it just handed back the first 5 rows of the file like they were personalized picks. Now it says flat out "you didn't give me anything to go on" and gives a spread of different genres instead.
- **numeric-only mid values** — normal, valid numbers, no bugs to trigger here. Included as a "does it still work normally" sanity check.
- **lofi but not acoustic** — `"lofi"` isn't a genre in this catalog. Before, it just silently failed to match anything. Now it explicitly says the genre wasn't recognized.

### Before guardrails
  ```
  === conflicting: metal + low energy: {'genre': 'metal', 'mood': 'aggressive', 'energy': 0.1} ===
Iron Verdict - Score: 5.26  (matches genre (metal); matches mood (aggressive))
Spacewalk Thoughts - Score: 1.64  (energy is a close match)
Moonlit Sonata Redux - Score: 1.60  (general match)
Library Rain - Score: 1.50  (general match)
Coffee Shop Stories - Score: 1.46  (general match)

=== out-of-range energy: {'genre': 'pop', 'energy': 5.0} ===
Gym Hero - Score: -3.14  (matches genre (pop))
Sunrise City - Score: -3.36  (matches genre (pop))
Iron Verdict - Score: -6.06  (general match)
Voltage Rush - Score: -6.10  (general match)
Storm Runner - Score: -6.18  (general match)

=== typo + wrong case: {'genre': 'Pop', 'mood': 'saad'} ===
Sunrise City - Score: 0.00  (general match)
Midnight Coding - Score: 0.00  (general match)
Storm Runner - Score: 0.00  (general match)
Library Rain - Score: 0.00  (general match)
Gym Hero - Score: 0.00  (general match)

=== empty profile: {} ===
Sunrise City - Score: 0.00  (general match)
Midnight Coding - Score: 0.00  (general match)
Storm Runner - Score: 0.00  (general match)
Library Rain - Score: 0.00  (general match)
Gym Hero - Score: 0.00  (general match)

=== numeric-only mid values: {'energy': 0.5, 'valence': 0.5, 'danceability': 0.5} ===
Midnight Coding - Score: 4.57  (energy is a close match; mood/positivity is a close match; danceability is a close match)
Fields of Amber - Score: 4.56  (energy is a close match; mood/positivity is a close match; danceability is a close match)
Focus Flow - Score: 4.52  (energy is a close match; mood/positivity is a close match; danceability is a close match)
Library Rain - Score: 4.43  (energy is a close match; mood/positivity is a close match; danceability is a close match)
Dust and Diesel - Score: 4.38  (energy is a close match; mood/positivity is a close match; danceability is a close match)

=== lofi but not acoustic: {'genre': 'lofi', 'likes_acoustic': False} ===
Midnight Coding - Score: 3.29  (matches genre (lofi))
Focus Flow - Score: 3.22  (matches genre (lofi))
Library Rain - Score: 3.14  (matches genre (lofi))
Voltage Rush - Score: 0.97  (general match)
Iron Verdict - Score: 0.96  (general match)
```

### After guardrails
```
=== conflicting: metal + low energy: {'genre': 'metal', 'mood': 'aggressive', 'energy': 0.1} ===
context query: (none — retrieval disabled)
guardrails:
    genre 'metal' was not recognised and could not be matched to a known value; ignored.
    mood 'aggressive' was not recognised and could not be matched to a known value; ignored.

recommendations:
  1. Baarishein — Anuv Jain
     indian · India · melancholic · score 1.96
  2. Scent of a Woman: Tango (Por Una Cabeza) — Carlos Gardel
     tango · Argentina · melancholic · score 1.94
  3. Kol Düğmeleri — Barış Manço
     anatolian rock · Turkey · melancholic · score 1.82
  4. 風雨不改 (電影《阿媽有咗第二個》主題曲) — Keung To
     cantopop · Hong Kong · melancholic · score 1.80
  5. 刻在我心底的名字 (Your Name Engraved Herein) - 電影<刻在你心底的名字>主題曲 — Crowd Lu
     mandopop · Taiwan · melancholic · score 1.80

=== out-of-range energy: {'genre': 'pop', 'energy': 5.0} ===
context query: (none — retrieval disabled)
guardrails:
    energy of 5.0 is outside 0.0-1.0; clamped to 1.0.
    genre 'pop' was not recognised and could not be matched to a known value; ignored.

recommendations:
  1. 新時代 - ウタ from ONE PIECE FILM RED — Ado
     j-pop · Japan · intense · score 1.98
  2. 祝福 — YOASOBI
     j-pop · Japan · celebratory · score 1.92
  3. Zombie — Fela Kuti
     afrobeat · Nigeria · celebratory · score 1.88
  4. Water No Get Enemy — Fela Kuti
     afrobeat · Nigeria · celebratory · score 1.86
  5. Mas Que Nada — Sérgio Mendes
     samba · Brazil · celebratory · score 1.86

=== typo + wrong case: {'genre': 'Pop', 'mood': 'saad'} ===
context query: (none — retrieval disabled)
guardrails:
    genre 'Pop' was not recognised and could not be matched to a known value; ignored.
    mood 'saad' was not recognised and could not be matched to a known value; ignored.
    No usable preferences were given; returning a diverse sample instead of a ranking.

no usable preferences — diverse sample, not a ranking:
  1. Water No Get Enemy — Fela Kuti
     afrobeat · Nigeria · celebratory · score 0.00
  2. For My Hand (feat. Ed Sheeran) — Burna Boy
     afrobeats · Nigeria · warm · score 0.00
  3. Ömrümün Sonbaharında — Barış Manço
     anatolian rock · Turkey · melancholic · score 0.00
  4. 風雨不改 (電影《阿媽有咗第二個》主題曲) — Keung To
     cantopop · Hong Kong · melancholic · score 0.00
  5. Bam Bam — Sister Nancy
     dancehall · Jamaica · celebratory · score 0.00

=== empty profile: {} ===
context query: (none — retrieval disabled)
guardrails:
    No usable preferences were given; returning a diverse sample instead of a ranking.

no usable preferences — diverse sample, not a ranking:
  1. Water No Get Enemy — Fela Kuti
     afrobeat · Nigeria · celebratory · score 0.00
  2. For My Hand (feat. Ed Sheeran) — Burna Boy
     afrobeats · Nigeria · warm · score 0.00
  3. Ömrümün Sonbaharında — Barış Manço
     anatolian rock · Turkey · melancholic · score 0.00
  4. 風雨不改 (電影《阿媽有咗第二個》主題曲) — Keung To
     cantopop · Hong Kong · melancholic · score 0.00
  5. Bam Bam — Sister Nancy
     dancehall · Jamaica · celebratory · score 0.00

=== numeric-only mid values: {'energy': 0.5, 'valence': 0.5, 'danceability': 0.5} ===
context query: (none — retrieval disabled)

recommendations:
  1. 你,好不好? - TVBS連續劇【遺憾拼圖】片尾曲 — Eric Chou
     mandopop · Taiwan · warm · score 4.81
  2. Deslizes — Fagner
     mpb · Brazil · melancholic · score 4.71
  3. 如果可以 - 電影"月老"主題曲 — WeiBird
     mandopop · Taiwan · melancholic · score 4.66
  4. Sodade — Cesária Evora
     morna · Cape Verde · melancholic · score 4.65
  5. Kesariya (From "Brahmastra") — Pritam
     indian · India · melancholic · score 4.65

=== lofi but not acoustic: {'genre': 'lofi', 'likes_acoustic': False} ===
context query: (none — retrieval disabled)
guardrails:
    genre 'lofi' was not recognised and could not be matched to a known value; ignored.

recommendations:
  1. Drive - Edit — Black Coffee
     south african house · South Africa · intense · score 1.00
  2. Turn Me On — Black Coffee
     south african house · South Africa · celebratory · score 1.00
  3. Give It To Me - Full Vocal Mix — Matt Sassari
     french · France · celebratory · score 1.00
  4. 夜に駆ける — YOASOBI
     j-pop · Japan · celebratory · score 1.00
  5. Shut Down — BLACKPINK
     k-pop · South Korea · celebratory · score 1.00
```

## Reflection

Read and complete `model_card.md`:

[**Model Card**](model_card.md)

Write 1 to 2 paragraphs here about what you learned:

- about how recommenders turn data into predictions
- about where bias or unfairness could show up in systems like this


