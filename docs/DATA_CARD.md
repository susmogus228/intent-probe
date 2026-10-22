# IntentProbe synthetic preference data

## Source and license provenance

All catalog descriptions, question wording and profile-generation code were
authored for this project. No third-party dataset or paper implementation was
copied. Research references in `RESEARCH.md` inform evaluation design, not data
provenance. There are no human respondents, scraped personal records or inferred
demographic attributes. Research citations document sources and do not transfer
licenses from external sources. This repository currently provides no project
license grant.

Generator version: `project-preferences-1.1`. Split seed: 42. The catalog contains
20 candidate briefs spanning structured data, language, vision, ML systems and
scientific ML. Fields specify estimated weeks, minimum hardware/experience,
domain, goal and tags. Estimates are authored assumptions, not verified delivery
times. The catalog is bounded and should not be presented as comprehensive.

## Profile construction and split integrity

Five hidden answers form a complete preference vector: four time budgets,
three hardware levels, three experience levels, five domains and three goals.
There are 540 possible vectors. A seeded permutation partitions 300 training,
80 validation and 120 test vectors, leaving 40 unused. Base profile IDs are
content-derived hashes of the vector, independent of split and utility family.
The same vector cannot cross splits even if its utility family differs.

Each vector has two grouped response variants: a truthful version and an
uncertain version. Normal uncertain replies replace one answer with `unknown`.
For the held-out answer-noise test cohort, uncertainty instead changes the
hardware answer and hides the goal. Those changed replies remain attached to
the original base profile. All generated training states, question labels and
response variants remain in the base profile's split.

Training and validation use balanced and specialist additive utilities. The
test cohort cycles between in-distribution, interaction-family shift, and
answer-noise conditions. The interaction family is absent from fitting and
validation. It is a narrow shift because many optimum sets remain unchanged.
Different test cohorts use different held-out preference vectors; they are not
causal paired estimates of the effect of shift on the same people.

## Utility and constraints

Time, hardware and current experience impose hard feasibility constraints.
Domain, desired outcome and matching complexity define bounded synthetic
utility. Several briefs can be tied for maximum utility. One-weekend profiles
have no feasible brief by construction and are deliberately retained.
Unknown constraints are integrated under a uniform finite prior; feasibility
shown in the app means feasibility against stated constraints, not certainty
about unstated needs. Indifference neutralizes a soft preference; unknown and
skipped answers do not assert indifference.

The evaluator alone receives true preference vectors and hidden utility-family
labels. Derived ML input arrays contain observed-state features only. Because
states are partial, different disjoint complete profiles may legitimately share
the same observed feature row. This is not a split of dialogue turns.

## Files and verification

The artifact directory contains:

- `data/catalog.json` and `data/questions.json`: the exact authored domain.
- `data/profiles.jsonl`: all generated profile variants with splits and labels.
- `data/split_manifest.json`: base IDs, record counts and per-split SHA-256.
- `data/training_rows.npz`, `data/validation_rows.npz`: observed feature arrays,
  regression labels and group IDs. Hidden fields are absent from features.
- `evaluation_profiles.json`: frozen held-out records for benchmark replay.
- `metadata.json`: generator/environment versions, global catalog/data hashes,
  model identity and limitations.

Canonical hashes use sorted JSON keys, compact separators and UTF-8, not a
platform-dependent pretty-printed representation. The model file has a separate
SHA-256 over its actual bytes. Replaying an experiment never adds profiles or
re-trains the model. User corrections to a saved session are application state,
not an online training mechanism.

## Limitations and evaluation populations

Synthetic profile counts do not mean real user counts. Utilities, unknown-answer
rates and incorrect-answer patterns are constructed assumptions. No fluency,
real satisfaction, fatigue, sensitive demographic fairness or superiority to an
LLM is measured. No-feasible detection is reported separately; such profiles
are excluded from the primary feasible-only regret denominator. Report raw
regret, synthetic cost-adjusted total loss and question counts together.

Hardware/experience/domain slices evaluate this simulator, not demographic
groups. Human preference collection or a public-use dataset would require a
separate design, consent/privacy review and new versioned provenance.
