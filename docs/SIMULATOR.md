# Opener calibration simulator

The Simulator tab generates 50 cases by default (1-200 supported). Use a set and
seed to reproduce inputs with the same catalogs/configuration. These are synthetic
calibration scenarios, not sampled probabilities of shops or combat outcomes.

Ten patterns cover one unit x4, all singles, two pairs, four copies plus support,
a 2-star-equivalent plus support, a sparse pair, off-direction units, component
mismatch, a missing essential augment and a mixed opener. Each block of ten uses
one shuffled ready composition as a reference; 50 cases cover up to five
compositions. Repeated blocks after exhausting the targets are allowed. The
reference composition is not a ground-truth label or a guaranteed winner.

Only cost 1-3 units are generated. Inventories contain copy counts, not simulated
board positioning. Offers contain up to three distinct logical augments of one
rarity, sourced from non-disabled variants explicitly available at 2-1.
Generator openers-v2 draws distinct loose components: 80% of cases have three,
10% have five, and 5% each have one or two. Largest-remainder allocation rounds
these proportions to the batch size, with seeded tie-breaking and shuffled order.
A batch of 50 contains 40/5 cases with three/five components and 2/3 cases with
one/two (or the reverse). Preferred components are sampled without replacement;
remaining slots use other distinct components from the catalog.

All unit copies together cost 7-14 gold, with at most four copies per unit.
Patterns are starting templates: excess support copies are removed to fit a
random budget, while spare budget buys units preferably outside the target opener.
The anchor copies are preserved when present. The UI displays the total unit cost.
The
anchor is a configured core when available, otherwise mainChampion if present
in the opener, otherwise the first opener unit; this is a generation choice and
never changes scoring or marks a unit core. Patterns remain synthetic; reviewers can label them unrealistic. No income/XP/trait/combat simulation
or automatic tuning is performed.

## Human evaluation

A separate full-width panel below ranking and review shows the selected final
composition with unit stars/hexes and assigned items. The review panel includes
matched/owned component counts from the saved score evidence.
New runs freeze final boards alongside results; replay retains those boards.
Older runs fetch the current configurator board with an explicit label, leaving
saved runs and their scores unchanged.

Select any composition in the case and rate it too low, about right, too high,
or unrealistic. Optionally enter expected unit points (shown out of that comp's
unit weight), expected overall score, and a comment. Unit expectations are stored
as a normalized 0-100 fit for comparison across weights. Save explicitly; draft
reviews persist while navigating cases in the tab. Discard a draft when unwanted.
Saved reviews survive refresh. Changing runs or exporting requires saving or
discarding drafts first.

## Artifacts and replay

Runs live at data/evaluations/simulator/<UUID>.json. Human reviews live separately
at data/evaluations/simulator/reviews/<UUID>/<caseId>.json. Writes use unique
sibling temporary files and atomic replacement. Runs freeze spots, full rankings,
compiled configurations, names/images, scoring/generator versions and an input
fingerprint. The directory is ignored by Git; Export JSON includes saved reviews.
Back up or export these files explicitly when you want to preserve/share them.

Replay evaluates exactly the old spots against current ready configurations and
engine code, producing a new immutable run. Old inventories retain their original
generator version and quantities, even when outside the new generation limits. It carries previous scores and prior
reviews as references; new reviews start empty. Existing runs and curated data
are never overwritten. Unknown references fail explicitly. Replay is the way to
compare scoring changes without changing the sample inputs.

API: GET/POST /api/simulator/runs, GET /api/simulator/runs/{id},
PUT /api/simulator/runs/{id}/reviews/{caseId}, and
POST /api/simulator/runs/{id}/replay. POST runs accepts setNumber, seed, count and
an optional sourceId to focus on one composition (currently API-only).


## Coverage and top-3 labels (v3)

The generator request accepts `mode: "standard" | "coverage"`. Standard preserves
openers-v2. Coverage uses coverage-v1: each case rotates to the next shuffled
composition, keeping the same inventory budget and component-count schedule;
for inventories with 2+ components the final component repeats the first. A
50-case run currently covers all 24 local compositions and has 48 duplicate cases.
This is deliberate stress coverage, not estimated live-game frequency. UI provides
the mode selector. Replay preserves the original spots and generator identity.

Reviews add `acceptableSourceIds` and `split` (calibration/holdout). Empty labels
mean unreviewed for ranking accuracy, even if a numerical review exists. The UI
can mark multiple acceptable directions and preserves those labels on save and
refresh. The benchmark reports top3HitRate only over labeled cases, excluding
unrealistic cases; null means no labeled evidence. Each split is reported
separately. A hit means at least one accepted direction appears in the assessed
top three. Reference labels on replay are compared against the new ranking.

Reproduce the comparison from the project root:

```bash
uv run python scripts/evaluate_recommendations.py --run RUN_UUID --coverage
```

Repeat `--run` to compare multiple runs. New runs are immutable local artifacts;
the command prints JSON containing changed top-3 lists, coverage, and labeled
metrics. It never assigns ground truth from the generator's reference composition.
See RECOMMENDATION_RESEARCH.md for the initial audit and limitations.
