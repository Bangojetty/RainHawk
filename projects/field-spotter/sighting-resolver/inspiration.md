# Inspiration — sighting-resolver

## Random query

> the curious habits of urban foxes after midnight

Used with the WebSearch tool. The sentence was invented as a freely
associated phrase — I deliberately picked a topic well away from the
previous feature's "dawn rituals / market towns" frame to avoid drift.

## Search results returned

1. Robert E. Fuller — *Urban foxes give up the secrets of rarely seen behaviour* — https://www.robertefuller.com/blogs/blog/urban-foxes-reveal-secrets-of-rarely-seen-behaviour
2. PMC (Nat. Lib. Med.) — *Urbanization does not affect red foxes' interest in anthropogenic food, but increases their initial cautiousness* — https://pmc.ncbi.nlm.nih.gov/articles/PMC11255992/
3. Wildlife Online — *Red Fox Activity* — https://www.wildlifeonline.me.uk/animals/article/red-fox-activity
4. AAAC Wildlife Removal — *What time are foxes most active at night?* — https://dallas.aaacwildliferemoval.com/blog/fox/what-time-are-foxes-most-active-at-night/
5. Cambridge Day — *Our city foxes have advantages, which is why there are more around to spot* — https://www.cambridgeday.com/2025/11/29/our-city-foxes-have-advantages-which-is-why-there-are-more-around-to-spot/
6. Birdsource — *Unveiling the Secret Lives of Urban Foxes* — https://www.birdsource.net/unveiling-the-secret-lives-of-urban-foxes
7. Useless Daily — *Urban Foxes: Adaptations and Survival in Cities* — https://www.uselessdaily.com/animals/urban-foxes-thriving-in-city-landscapes/
8. Discover Wild Science — *Foxes in the City: How Urban Britain Became a Wildlife Laboratory* — https://discoverwildscience.com/foxes-in-the-city-how-urban-britain-became-a-wildlife-laboratory-1-319698/
9. Westchester Wildlife — *Understanding the Behavior and Habitat of Foxes in Suburban Areas* — https://westchesterwildlife.com/blog/foxes-in-suburban-areas/
10. Natural History Museum — *The secret life of urban foxes* — https://www.nhm.ac.uk/discover/the-secret-life-of-urban-foxes.html

## Chosen URL

**Picked:** result #1 — *Urban foxes give up the secrets of rarely seen
behaviour* by Robert E. Fuller. **Why:** I tried the NHM article first,
but its server returned 403 to the WebFetch tool. I picked the Fuller
piece next because it's a primary-observation account from a wildlife
photographer — first-person sightings, counts, descriptions of family
behaviour — which is closer to what an actual user of a "sighting log"
tool would produce, and therefore richer raw material for synthesizing a
concrete tool than a popular-science overview would be.

URL: https://www.robertefuller.com/blogs/blog/urban-foxes-reveal-secrets-of-rarely-seen-behaviour

## Captured sentences (sampled across the article)

1. "There were rabbit remains and discarded pigeon and pheasant wings and tail feathers."
2. "Fox cubs are very adventurous until they are about 10-13 weeks old and reach what is known as the 'neophobic' stage."
3. "The dog fox bounding skilfully on top of a 6ft high wooden boundary fence."
4. "It took me several attempts before I finally counted a total of 10."
5. "Foxes rarely have more than six cubs in one litter."
6. "The feathers had been chewed at the ends in a way few predators - except foxes - do."
7. "I could even smell the musky aroma of fox."
8. "The two vixens had joined forces to raise their cubs together."
9. "It was years before they chose to use their bespoke home."
10. "I have watched foxes in the countryside for decades, but with their sharp eyes, acute hearing and excellent sense of smell, sightings here are all too brief."

## Themes I extracted

- **Counting is hard, brief, and error-prone.** "It took me several
  attempts before I finally counted a total of 10." — Repeat sightings
  of foxes are easily double-counted; a tool that helps disambiguate
  observations into distinct individuals would be useful.
- **Distinguishing features matter.** Cubs vs adults, dog-fox vs vixen,
  individual markings — these are the per-sighting attributes that
  enable disambiguation.
- **Family groupings are real.** "The two vixens had joined forces" —
  the disambiguation result naturally exposes group structure too.
- **Movement constraints.** A 6ft fence is no obstacle, but a fox can
  only travel so fast. Spatial-temporal compatibility is a constraint
  on whether two sightings could be the same individual.
