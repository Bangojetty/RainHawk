# Feature idea — sighting-resolver

## The idea (plain English)

Given a chronological list of timestamped point-sightings of a species —
each with a location (planar metres), an optional set of distinguishing
features (size class, age class, coat markings, sex), and a notion of
how fast the species can plausibly travel — produce an estimate of how
many distinct individuals the observer actually saw, plus a partition of
the input sightings into per-individual tracks. The resolver should
reject impossible same-individual links (sightings further apart than
the species could have travelled in the time gap, or whose features
conflict) and accept compatible ones, and it should return a structured
result with an estimated count, the assignments, and a confidence score
per cluster reflecting how well-constrained that cluster is.

## Rationale — tying back to the captured sentences

Two of the captured sentences shape this feature directly. *"It took me
several attempts before I finally counted a total of 10."* describes
exactly the problem: an observer keeps sighting "a fox" and has to
mentally reconcile which sightings are the same animal and which are
different. *"The two vixens had joined forces to raise their cubs
together."* shows that the same observation log can simultaneously
contain multiple adults and multiple cubs in close proximity — meaning
the disambiguator has to use distinguishing features (sex, age class) to
keep them apart, not just space and time. *"The dog fox bounding
skilfully on top of a 6ft high wooden boundary fence."* confirms a key
modelling assumption: a fox can move quickly through a small territory,
so a generous max-speed threshold is more important than a tight one.

The smallest interesting kernel of those observations is a clusterer
that takes (sightings + species movement params) and returns an
estimated individual-count plus a labelled partition, rejecting
infeasible groupings with a clear reason. That is what this feature
builds.
