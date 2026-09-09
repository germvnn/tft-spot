# TFT Spot - Architecture and Domain Decisions

- ADR-001 (Accepted): raw source data is immutable.
- ADR-002 (Accepted): use apiName as the integration identifier.
- ADR-003 (Accepted): preserve TFT Academy IDs as sourceId.
- ADR-004 (Accepted): Composition.sourceId is guide.id, not compSlug.
- ADR-005 (Accepted): separate raw, normalized, and scoring concerns.
- ADR-006 (Accepted): do not filter during normalization.
- ADR-007 (Accepted): preserve source array order.
- ADR-008 (Accepted): do not infer carousel semantics yet.
- ADR-009 (Accepted): do not infer augmentTypes scoring semantics yet.
- ADR-010 (Accepted): MVP scoring has component, augment, and unit dimensions.
- ADR-011 (Accepted): keep architecture intentionally simple.
- ADR-012 (Accepted): keep source snapshots under `data/raw/<source>` and UI assets
  under `data/assets`; application data must not live inside the Python package.
- ADR-013 (Accepted): downloaded data is reproducible, excluded from Git, and
  generated with one standard-library Python command.
- ADR-014 (Accepted): curated bootstrap preserves existing non-`unset` decisions,
  fills missing component priorities with `high` and augment priorities with
  `medium`, then marks every composition `ready` in source array order.

- ADR-015 (Accepted): MVP recommends direction at stage 2-1, scoring each composition
  with each offered augment independently. Only listed, non-avoid augment options
  are eligible. One essential augment at most is a hard requirement; essential
  components and units remain preferences.
- ADR-016 (Accepted): curated early-unit priorities multiply the copy signal
  0,1,3,5,8,13,21,34,55,89. Initial unit normalization uses 21 weighted points.
  Component fit measures use of owned loose components, capped by the existing
  configurator demand tally. Priority multipliers are 1/.75/.5/.25/0. See SCORING.md.
- ADR-017 (Accepted): fixed curated dimension weights produce a 0-100 matching
  score, never a probability or a candidate-relative scale. Return explanations
  and unavailable reasons. Legacy unit priorities default to medium on read;
  no curated or raw snapshot is rewritten by scoring.

- ADR-018 (Accepted): Recommendations is the default application tab; Configurator
  is a separate setup/patch view. Both stay mounted after first use to retain
  in-progress input across tab changes. Returning to Recommendations invalidates
  old results so updated curation is reflected by the next ranking request.
- ADR-019 (Accepted): the player picker counts copies with left-click +1 and
  right-click -1 (minimum zero), including copies inside starred units. Costs
  1/2/3 use gray/green/blue borders; higher costs are excluded only from this UI.
  A shared rarity dropdown filters the three augment slots. Generate ranking
  explicitly below the input; editing the spot invalidates previous results.

- ADR-020 (Accepted): group offered augment choices by exact (tier, name), scoped
  to their set. Resolve all source apiName aliases in both offers and compiled
  composition decisions, including essential gates. Preserve source/curated data.
  Equal-priority duplicate decisions collapse; conflicting priorities produce
  an explicit error naming the composition instead of choosing a priority silently.
- ADR-021 (Accepted): curated early-unit decisions gain core: false by default.
  The flag survives save, bootstrap and compilation and is exposed in evidence.
  It does not yet change scores or eligibility. Core-unit semantics and stronger
  early-pair signals for 1/2-cost reroll require calibration with player examples.

- ADR-022 (Accepted, supersedes unit scoring in ADR-016/021): cap each champion's
  copy signal at four copies (0/1/3/5/8). Unit scoring uses core only; legacy unit
  priorities have no scoring/readiness effect. For n core units, their share is
  1 - 0.25/n and their score is the average signal divided by 8. Non-core signal
  saturates at 4 points for the remaining share. Without core, all opener signals
  saturate at 8 points. See SCORING.md v2 for examples and missing-unit semantics.

- ADR-023 (Accepted, updates ADR-014): new or missing component priorities default
  to essential (Core). Bootstrap also fills unset components with essential.
  Existing explicit priorities are preserved; no bulk migration is performed.

- ADR-024 (Accepted, updates ADR-022 no-core fallback): without configured core,
  average the capped copy signals over all configured opener units. Each unit
  has equal weight; extra copies cannot substitute for missing opener units.
  Empty openers score zero. Core/support scoring is unchanged.

- ADR-025 (Accepted, updates ADR-024): no-core unit signals are 0 when absent,
  otherwise 4 + min(copies, 4), averaged across all opener units over a maximum
  signal of 8. This gives 10/40 for one unit x4 in a four-unit opener and 28.75/40
  with the other three units present. Core/support scoring remains unchanged.
- ADR-026 (Accepted): the Simulator generates seeded synthetic calibration cases,
  not combat outcomes or an estimate of real opener frequencies. Freeze spots,
  compiled inputs, input fingerprint, versions and rankings in local JSON runs.
  Save human reviews separately; replay exact spots against current configurations
  into a new run with prior scores for comparison. Never auto-tune weights from
  reviews and never modify source or curated data during simulation.


## ADR 027 — Stage 2-1 simulator inventory limits

Per user calibration assumptions, openers-v2 generates unique component types,
with batch proportions 80% three, 10% five, 5% one and 5% two (largest remainder
rounding with seeded ties). Unit inventory costs 7-14 gold in total and contains
at most four copies of any cost 1-3 unit. Templates are adjusted to fit this
budget, preferring off-direction filler. This changes generation, not scoring.
Frozen old runs and exact replay inputs remain unchanged. See SIMULATOR.md.


## ADR-028 — Explainable stage 2-1 item plans and expert conditions

Accepted following the user's explicit implementation authorization on 2026-09-08.
Scoring v3 keeps the existing unit curve and dimension weights. For supported
item contexts and 2-10 components, component fit is 75% existing resource fit
and 25% executable item-plan fit. Larger inventories or missing item context
retain the legacy component score. These are initial calibration constants.

A plan respects duplicate recipes, three slots per current holder and selected
future holder, and single credit for each of Burn/Wound, Sunder and Shred.
It does not promise a win streak or model combat. Role affinities are conservative
priors; explicit champion exceptions override source builds and those priors.
No heuristic is inferred for Specialists or missing roles. Manual augment
conditions require copies and optionally an individually buildable compatible
item. Their summed adjustment is capped at +/-20 augment-fit points and the
result at 0-100. Required/avoided augment gates remain independent.

Alternative openers are configured explicitly and scored separately using the
existing unit rules. The best unit fit is selected; units across variants are
not combined. Existing core flags remain authoritative. A missing augment entry
is now `unassessed`, with null overall score and separately visible resource
fits. This is distinct from blocked/avoid, with no invented neutral augment fit.

## ADR-029 — Coverage and human-labeled recommendation evaluation

Keep openers-v2 unchanged as the default. An opt-in coverage-v1 stress generator
rotates across ready compositions every case and repeats a component in cases
with at least two components. It is not a distribution of real games. Reviews
may label several acceptable compositions and assign the case to calibration or
holdout. Top-3 hit rate counts only labeled, realistic cases in each split.
Frozen replay inherits prior labels as references; no weights are auto-tuned.
