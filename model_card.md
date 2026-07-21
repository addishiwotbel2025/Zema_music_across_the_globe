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