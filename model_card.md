# 🎧 Model Card: Music Recommender Simulation

## 1. Model Name  

Music Recommender  
Example: **VibeFinder 1.0**  

---

## 2. Intended Use  

Describe what your recommender is designed to do and who it is for. 

Prompts:  

- What kind of recommendations does it generate  
    it generates recommendations mostly based on genre, then the score lowers to energy and mood then danceability
- What assumptions does it make about the user  
    that genre is the most important thing
    some behviors align such as acoustics and likes_lofi, it might be two different things for a user but the absence of one affects the overall score immensely
- Is this for real users or classroom exploration  
    it is for class exploration because there are many biases
---

## 3. How the Model Works  

Explain your scoring approach in simple language.  

Prompts:  

- What features of each song are used (genre, energy, mood, etc.) 
    favorite_genre
    favorite_mood
    target_energy
    likes_acoustic
    favorite_artist
    target_valence
    target_danceability
- What user preferences are considered 
    The recommender listens to what you tell it about your taste: your favorite genre and mood, how much energy you want, whether you like acoustic songs, and optionally a favorite artist and how positive or danceable you want the music to feel. You don't have to fill in all of them — you can give just a few, and it works with whatever you share.
- How does the model turn those into a score  
    Each song starts with 0 points and earns points for every preference it matches. Matching your genre is worth the most, mood and energy are worth a fair bit, and things like danceability, acoustic feel, and artist add smaller bonuses. The closer a song's energy (or danceability) is to what you asked for, the more of those points it keeps. Add it all up and every song gets a total score — then the songs with the highest scores rise to the top of your list.

- What changes did you make from the starter logic  
    I added more features such as artist even if it has a low score, it is something I personally consider in my song recommendations


---

## 4. Data  

Describe the dataset the model uses.  

Prompts:  

- How many songs are in the catalog  
    18 songs
- What genres or moods are represented
    Genres (15): ambient, classical, country, edm, folk, hip hop, indie pop, jazz, lofi, metal, pop, r&b, reggae, rock, synthwave

    Moods (14): aggressive, carefree, chill, confident, energetic, focused, happy, hopeful, intense, melancholic, moody, nostalgic, relaxed, romantic

- Did you add or remove data 
    yes, I added 8 more datas
- Are there parts of musical taste missing in the dataset  
    yes, some of them don't have all the features, but they all have the fundamental 4.
---

## 5. Strengths  

Where does your system seem to work well  

Prompts:  

- User types for which it gives reasonable results  
    when all the features are available. the more the feature, the more accurate it is

    It works best for people who have a clear, single-genre taste — like "I want happy pop" or "give me chill lofi." When someone knows the genre and mood they're after, the recommender lines up sensible songs at the top. My jazz, afrobeat, and latin profiles all gave clean, believable top-5 lists.

- Any patterns you think your scoring captures correctly  
    It correctly rewards songs that match on several fronts at once. A song that's the right genre and the right mood and close to your energy level rises to the top, which is exactly what you'd expect. It also does a good job ranking within a genre — for example, when I asked for acoustic lofi, the most acoustic lofi songs came out on top in the right order.
- Cases where the recommendations matched your intuition 

I made my own song lists with most and least preferences.
    For my "happy latin" profile, the classic party songs (Despacito, Bailando, Vivir Mi Vida) swept the top spots — exactly what I'd hand someone who asked for upbeat latin music. Same with jazz: "Fly Me to the Moon" led for a romantic jazz mood, which felt right. The energy matching also behaved sensibly — when I wanted moderate energy, mellow songs beat the high-intensity ones.
---

## 6. Limitations and Bias 

Where the system struggles or behaves unfairly. 

Prompts:  

- Features it does not consider 
    it doesn't consider edge cases like "saad" instead of sad.
    it doesn't have a range check so, it might add negative values which really skew results.
- Genres or moods that are underrepresented 
    genre is the most deciding factor so, other things such as energy and mood might be unrepresented.

- Cases where the system overfits to one preference  
    if we take out mood, it will be solely on energy and danceability and that doesn't provide and accurate recommendation when it comes to lofi and jazz songs since they heavily rely on mood
- Ways the scoring might unintentionally favor some users  

---

### 6b. Limitations of the scaled-up (culturally aware) version

Notes captured while profiling the source data, before building. Written down early so
they don't get lost or quietly forgotten once the system starts producing nice-looking output.

#### Source data

The catalog is built from a public Spotify-derived dataset: **114,000 tracks, 114 genre labels**
(many write-ups say 125; the file has 114). Every label holds exactly 1,000 rows, so the dataset
was assembled by filling a quota per label rather than by sampling music as it exists.

Profiling the top tracks of 30 candidate labels showed that most labels do not describe their
contents.

**1. Unreliable genre labels**

| Label | Actually returns | Verdict |
|---|---|---|
| `latin`, `latino`, `reggaeton`, `reggae` | **Identical** top tracks — Bad Bunny, Manuel Turizo | 4 labels, 1 bucket |
| `world-music` | Hillsong, Bethel Music, Chris Tomlin — worship pop | wrong |
| `afrobeat` | Led by Calle 13, a Puerto Rican rap group | wrong |
| `ska` | Led by The Offspring | wrong |
| `dub` | Led by ILLENIUM, Porter Robinson | wrong |
| `brazil` | EDM producers | wrong |
| `pagode` | Anitta | wrong |
| `iranian` | Diaspora ambient/metal, popularity 20–35 | unusable |
| `forro` / `sertanejo` | Same artists as each other | duplicated |

About 14 of the 30 held up, including `tango`, `salsa`, `indian`, `turkish`, `j-pop`, `k-pop`,
`mandopop`, `cantopop`, `mpb`, `samba`, `french`, `spanish`, `swedish`. That some labels work is
what makes the broken ones diagnosable rather than uniform noise.

**2. The first reading of that evidence was wrong**

An initial pass concluded that `afrobeat` held no Fela Kuti and `reggae` no Bob Marley. Both were
false — 5 Fela tracks and 10 Marley tracks are present, and Cesária Évora sits inside
`world-music`. They were simply outranked: Bad Bunny scores 94–98 and buried Marley at 78; Calle
13 at 75 buried Fela at 48.

> The labels are **polluted**, not empty — and sorting by popularity surfaces the pollution first.

The profiling method carried its own bias. Popularity-ordered sampling showed the loudest entries,
not the representative ones.

**3. The taxonomy is a browse menu, not a classification**

Roughly fifteen of the 114 "genres" are moods, contexts, instruments, or franchises rather than
genres: `happy`, `sad`, `chill`, `study`, `sleep`, `party`, `romance`, `comedy`, `kids`, `disney`,
`anime`, `guitar`, `piano`, `show-tunes`, `groove`.

**4. Uneven representation**

| Category | Labels |
|---|---|
| Japan | 4 |
| Metal | 6 |
| **Entire African continent** | **1, mislabelled** |
| "Everywhere else" | 1 (`world-music`, holding worship pop) |

No Ethiopian, Arabic, North African, South African, Andean, Balkan, or Indigenous category exists.
"Diverse" here means *diverse within one Western streaming platform's browse menu*.

**5. Response: select by artist, not by label**

| Field | Source |
|---|---|
| `energy`, `valence`, `danceability`, `acousticness`, `tempo` | Kept — measured per track, unaffected by mislabelling |
| `artists`, `track_name` | Kept — correct |
| `genre`, `region`, `mood` | **Assigned by hand** |

The music was mis-filed, not missing. Verification then covers a readable list of ~80 artist names
instead of 114,000 unverifiable rows.

This substitutes one curator's bias for the platform's, which is not automatically an improvement —
a different curator produces a different list. Its only real advantage is that the list is
*inspectable*, where the platform's labelling is undocumented. It also does not scale: it works at
100 songs because a human can check 100 songs, which is exactly why the original labelling was
automated and wrong.

**6. Traditions that could not be recovered at all**

Searching all 114,000 rows by artist name returned nothing for Arabic and North African music
(Umm Kulthum, Fairuz, Amr Diab, Rachid Taha), Senegalese music (Youssou N'Dour, Baaba Maal),
Southeast Asian music (Rhoma Irama, Iwan Fals), or Miriam Makeba. Ethiopian music yielded exactly
one artist, Mulatu Astatke; Mahmoud Ahmed, Aster Aweke, Teddy Afro and Tilahun Gessesse are all
absent.

The finished catalog therefore contains **one Ethiopian artist and zero Arabic ones**. This is a
hard gap that no amount of cleaning closes.

**7. Mechanical defects — these are fixable**

| Defect | Scale | Fix |
|---|---|---|
| Duplicate `track_id` | 21.3% of rows; 16,641 tracks under multiple labels | Deduplicate |
| `tempo` of 0 | Not a possible tempo | Drop or flag |
| Missing `artists` / `track_name` / `album_name` | 1 row | Drop |

These are cleaning problems: the value is malformed and a rule fixes it. The label problem is not —
the field is well-formed and the content is simply wrong. That is a *fitness-for-purpose*
limitation, and the only honest responses are to narrow scope, cross-check elsewhere, and
disclose. Disclosure is the part that is not optional.

**8. Limits of the audio features themselves**

- **Proprietary and opaque.** `energy`, `valence`, `danceability`, and `acousticness` are
  Spotify's derived metrics with no published methodology, so "energy 0.82" cannot be
  independently verified.
- **No longer reproducible.** The `audio-features` endpoint was deprecated on 27 November 2024
  with no replacement, making this dataset a frozen snapshot.
- **Platform coverage is a bias.** Only music distributed on Spotify can appear; much traditional,
  regional, devotional, and non-commercially-released music is absent.
- **Popularity skew** under-represents older recordings and non-anglophone catalogues.

#### Cultural representation

- **Genre is a weak proxy for culture.** The system uses genre (and artist) to infer a `region`,
  but a genre label is not a culture, and an artist's nationality is not the culture a song
  belongs to. Treating them as equivalent is a simplification the user never sees.
- **The `mood` field is derived, not measured.** The source data has no mood column, so mood is
  computed from the valence/energy quadrant. That mapping is an invention of this project.
- **Mood categories are not culturally neutral.** Emotional categories do not translate cleanly
  between musical traditions. Ethiopian *tizita* and Portuguese *saudade* both get flattened into
  something like "nostalgic" or "sad", which loses most of what the word actually means. The
  vocabulary of moods is itself a Western-inflected choice.
- **The RAG corpus is unevenly rich, in a way that works against the project's goal.**
  Cultural context is retrieved from Wikipedia, whose coverage is far deeper for Western and
  anglophone artists than for many non-Western ones. So the system will produce its most
  detailed, most convincing cultural explanations for exactly the music that needs the least
  explaining — and its thinnest for the music the project exists to surface. Confidence in the
  output will not correlate with how well the system actually understands the tradition.
- **English Wikipedia carries an anglophone editorial perspective**, including in how it frames
  non-Western musical traditions.
- **Risk of stereotyping by inferred identity.** A system that recommends "culturally" can easily
  slide into inferring a user's ethnicity or nationality and then narrowing their results to it.
  That is both offensive and simply a worse recommender. The design response: the system keys off
  *stated taste and occasion only*, never inferred identity. A user volunteering where they are
  from is treated as one soft signal among many, never as a filter. Requests framed as
  "what do people from X listen to" are reframed rather than answered.

#### System design

- **Content-based only.** There is no collaborative signal — no "people who liked this also liked"
  — and no learning across sessions from what a user accepts or skips. Recommendations depend
  entirely on the stated profile and the song features.
- **Strategy escalation can degrade silently if disclosure fails.** When a step does not work, the
  system tries a genuinely different method rather than repeating itself: retrieval falls back from
  exact filtering, to semantic search, to progressively dropping constraints; unknown values are
  normalised, then fuzzy-matched, then ignored; an unrankable profile switches from scoring to a
  diverse sample; a missing cultural note falls back from song, to artist, to genre level, and
  finally to making no cultural claim at all. The risk is that a result produced on the fifth rung
  of a fallback ladder looks exactly as confident as one produced on the first. Every response
  therefore has to report which strategy produced it — and that reporting is the part most likely
  to get quietly dropped under time pressure.
- **Fallbacks can mask real bugs.** A system that always returns something will keep returning
  something when the cause is a genuine defect rather than a hard input. The trace log exists partly
  so that a rising fallback rate stays visible instead of invisible.
- **Explanations are templated, not generated.** With no LLM in the pipeline, explanations are
  assembled from the score breakdown and retrieved text. This makes them grounded by construction
  (nothing can be fabricated) but noticeably less fluent than model-written prose.
- **Grounded is not the same as correct.** Every claim traces to a retrieved passage, but a
  passage can itself be wrong or out of date. Citation proves provenance, not truth.
- **User-set feature priorities can degenerate.** If a user prioritises everything, they have
  prioritised nothing. Weights are renormalised to keep total weight constant, which means
  raising one feature necessarily lowers others — a trade-off the user is not shown.
- **The diversity cap is deliberately blunt.** Limiting how many songs one artist or region may
  occupy in the top 5 will sometimes exclude a genuinely better-scoring match. This trades
  accuracy for variety on purpose, but the user is not told a song was dropped.
- **Known scoring bugs carried over from v1** (fixed in the guardrail stage, recorded here
  because they are what motivated it): out-of-range input produced negative scores,
  capitalisation mismatches silently failed to match, unknown values such as `saad` were ignored
  without warning, and an empty profile returned the first five rows of the file dressed up as
  a ranking.

---

## 7. Evaluation  

How you checked whether the recommender behaved as expected. 

Prompts:  

- Which user profiles you tested  
    Tested contradicting behaviors such as a lofi preference but no acoustic preference. 

    Omitting likes_acoustic is not neutral in the way you'd expect — it's its own third behavior. True rewards acousticness, False penalizes it, and omitted ignores it and leaves songs tied on genre alone. So "no preference" produces a flat, order-of-file tie rather than a balanced ranking.

- What you looked for in the recommendations  

- What surprised you  
    we also have to consider egde cases such as empty input
- Any simple tests or comparisons you ran  

    Think of it like asking a DJ for a "happy pop song." The DJ mostly hears "pop" and barely registers "happy" — so they throw on a loud, high-energy pop banger that gets the crowd moving but isn't actually happy. It's still pop, still a hit, so to the DJ it's close enough — even though it missed the mood you asked for.

    That's the recommender: it treats the genre (pop) as the main request and the mood (happy) as a minor detail, so a right-genre/wrong-mood song keeps getting picked.

    - **Adversarial profiles:** out-of-range `energy` gave negative scores; typos/wrong-casing and empty `{}` silently returned songs in file order.
    - **`likes_acoustic` (omit vs True vs False):** three distinct behaviors — omitting ignores acousticness (genre-only tie), True rewards it, False penalizes it.
    - **Weight shift (2× energy, ½ genre):** swapped ranks #2/#3 toward the closer energy fit; the #1 pick was unchanged.
    - **Mood removal:** minor on the generic dataset, but decisive on my jazz/afrobeat/latin list — dropped the jazz #1 from 1st to 4th and broke the latin "happy" sweep.


---

## 8. Future Work  

Ideas for how you would improve the model next.  

Prompts:  

- Additional features or preferences 
    Let users pick more than one genre at a time. Right now the recommender only accepts a single genre, so my "I love jazz, afrobeat, and latin" taste had to be split into three separate profiles. Supporting a list of genres would let it build one mixed playlist. I'd also add tempo (BPM) as a preference, since that matters for things like workout or study playlists.

- Better ways to explain recommendations 
    Show how much each reason mattered, not just that it matched. Instead of "matches genre, energy is close," it could say something like "mostly because it's pop, with a small boost for energy." It would also help to explain why a song didn't make the list, so the reasons feel more honest.
- Improving diversity among the top results  
- Handling more complex user tastes  
    Handle contradictory or partial preferences more gracefully. Today, leaving out a preference, or asking for something like high energy but a sad mood, produces confusing results with no warning. The recommender could detect these cases, ask a follow-up, or clearly flag that it made a trade-off — and it should reject impossible inputs (like an energy value out of range) instead of silently producing negative scores.
---

## 9. Personal Reflection  

A few sentences about your experience.  

Prompts:  

- What you learned about recommender systems  
    they are not perfect and scoring systems are rigid.

    my biggest learning moment during this project is the gaps in this scoring system and why other options such as collaborative or content-based recommendations are used

    also, I understand how music recommendations work, its like a game that has a score and the song who is a winner gets recommended. It pretty much works like game scoring because there is also a penalty.

- Something unexpected or interesting you discovered
    heavily relying on a few features is not good
    personally, I never considered myself to be interested in many features all at once and I categorize myself. I feel like AI does a good job of creating a profile of a person even without them knowing what they like, and they listen to how they feel
- How this changed the way you think about music recommendation apps  
    I thought that they were more complicated than this (the better the recommender the more complicated it is)
    but it is good to understand the base idea of it. 
    this means that there is a potential for music recommenders to be tailored to a user to decrease bias. A user can choose to weigh genre morethan mood or energy in this case.

How did using AI tools help you, and when did you need to double-check them?
    sometimes, AI runs tests or recommends a change in code without saying anything -- just asking permission. I think it is best to ask for explanations before changing code and have a perspective on why the change might be useful instead of just accepting updates.

What would you try next if you extended this project?
    I would try recommendations based on for example cultural background. There are people who value diversity and exploration of songs across the world more than any of these features

What surprised you about how simple algorithms can still "feel" like recommendations?
    they might work for perfect users but they are not good fits for real world use.