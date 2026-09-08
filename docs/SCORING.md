# Stage 2-1 matching, version 2.1

The engine recommends a direction at the first augment choice. Its 0-100 score
measures resource matching, not win probability or final-board completion.
Only loose components, owned units and the currently offered augments are inputs.
Gold, XP, stage progression, finished items, scouting and combat simulation are
outside this version. Economic direction is represented by curated augment fit.

## Priorities and eligibility

Component/augment priority multipliers: essential 1, high 0.75, medium 0.5, low 0.25, avoid 0.
Unset component/augment decisions and draft configurations cannot enter the engine.
Each composition may have at most one essential augment, even while draft.
If present, only selecting that augment makes the composition eligible.
Other offered augments cannot compensate for the missing requirement.
Only listed augments are considered; avoid entries are excluded from selection.
Essential components are strong preferences, never eligibility gates. Legacy unit
priorities are accepted for compatibility but have no scoring or readiness effect.
Source augment order and augmentTypes do not imply importance. Source disabled
metadata is not an additional gate: the actual offer and curated priorities govern.

## Unit fit

Inventory entries identify a champion by apiName and contain stars (1-3) and count
(the number of owned units at that star level). Aggregate across board and bench:
`copies = sum(count * 3 ** (stars - 1))` for each apiName.

Copies map to `0, 1, 3, 5, 8` for 0, 1, 2, 3, 4+ copies. Each champion's
signal saturates at four copies, including copies inside upgraded units.
There is no unit-priority multiplier: core is the sole per-unit scoring setting.

When n configured units are core:

- `coreShare = 1 - 0.25 / n`: 75% for one, 87.5% for two, 91.67% for three.
- `coreScore = 100 * sum(coreSignals) / (8 * n)`.
- `supportScore = min(100, 100 * sum(nonCoreSignals) / 4)`.
- `unitFit = coreShare * coreScore + (1 - coreShare) * supportScore`.

Core importance depends on configured core count, not just the ones owned.
Missing core contributes zero to the average; extra copies of another core cannot
substitute for it. Support saturates at four signal points (four singles or a
pair plus a single). Missing support is not redistributed to core, even if no
support units are configured. Four copies of the only core alone give 75 unit fit;
with three support singles they give 93.75 fit, or 37.5 of a 40-point unit weight.

Without any configured core, each configured opener unit has equal weight:
`unitFit = 100 * sum(signals) / (8 * numberOfOpenerUnits)`.
Each unit caps independently at four copies; copies of one cannot substitute for
other opener units. With four opener units, Veigar x4 alone gives 25 unit fit
(10/40), and adding three support singles gives 34.375 fit (13.75/40).
An empty opener or empty inventory yields zero. This averaging applies only
when no core is configured; the core/support formula above remains unchanged.
Raw earlyComp stars remain reference information.

The response exposes core count/share, core/support fit, their contributions,
and each unit's raw copies and capped signal. These initial v2 calibration
constants are documented and covered by example-based tests; they can be refined
with further player feedback. Augment eligibility and total dimension weights
remain independent of this unit calculation.

## Component fit

Aggregate owned quantities by apiName. For each component, credit at most the
requiredCount already exposed by the configurator, multiplied by its priority.
That count is the configurator's recipe/direct-component tally, used as an MVP
capacity heuristic; it does not prove the source carousel is a complete build.
No priority is inferred from carousel order.

`componentFit = 100 * sum(creditedCount * priority) / totalOwnedComponents`.

Empty inventory gives zero. Unlisted, avoided and excess components give zero
credit but remain in the owned inventory denominator. Missing future components
are not in the denominator. Each physical component is credited at most once.
Two useful high-priority bows with capacity two give 75 component fit. With three
owned bows and capacity two, fit is 50. Finished items are rejected by the API.

## Augments and combined ranking

For every offered augment, evaluate a separate scenario:
`augmentFit = 100 * priority` for eligible listed options.

`score = (unitFit * weights.units + componentFit * weights.components +
          augmentFit * weights.augments) / 100`.

Weights retain their curated values and sum to 100. Missing evidence does not
redistribute weights. The best eligible scenario is the composition's result.
Unavailable scenarios have score null, an eligibility flag and a reason code.
No scores are normalized against other candidates. Ties preserve source order;
augment ties preserve offer order. No tier, publication or cost filter is applied.

The response includes all offer scenarios, dimension scores, weighted contributions,
copy signals, component quantities and the required augment. Draft compositions
are explicitly reported in skipped. Broken references fail with explicit errors.

## Configuration compatibility

Schema version 1 gains an additive units decision list. Older files without it
receive medium priorities for distinct earlyComp apiNames on read, without file
writes. Saving or bootstrapping persists these decisions. Bootstrap preserves
existing priorities and fills unset unit decisions with medium. Ready saves must
cover every current unit, component and augment candidate. Units need only apiName
and core (default false); legacy priority is retained but ignored. Duplicate decisions,
unknown references and stored source/set identity mismatches are rejected.

The compiler consumes the existing resolved configurator workspace and produces
EngineComposition. Scoring itself performs no filesystem or source parsing work.
This adapter does not complete the broader normalization milestones in ROADMAP.

## API

POST /api/recommendations with JSON (replace example identifiers with catalog apiNames):

```json
{
  "setNumber": 18,
  "offeredAugments": ["AUGMENT_A", "AUGMENT_B", "AUGMENT_C"],
  "units": [{"apiName": "CHAMPION_A", "stars": 2, "count": 2}],
  "components": [{"apiName": "COMPONENT_A", "count": 2}]
}
```

One to three distinct offers are accepted for partial UI entry. Units and components
may be empty, but supplied quantities must be positive integers. The API validates
inventory references and component types, rejects unsupported sets and returns
scoringVersion, recommendations and skipped. The Recommendations tab uses this
endpoint and GET /api/spot-catalog; the Configurator tab edits curated inputs.

## Augment alias resolution (v1.1)

Within a set, equal raw (tier, name) values identify one selectable augment.
The first source apiName represents the group. Before scoring, both offered
augment IDs and curated decisions resolve through this alias map. Essential
requirements therefore match any variant. Multiple identical-priority decisions
in one group collapse into one; conflicting priorities fail explicitly. An offer
containing two aliases of the same logical augment is rejected as a duplicate.
Catalog entries include all aliases and per-variant source metadata. Curation
continues to preserve original source apiNames; grouping never rewrites raw files.

## Core-unit compatibility

Unit decisions default core to false and legacy priority to medium. Saved
priorities, including unset, no longer affect unit scoring or ready validation.
The UI exposes only the core checkbox. Bootstrap preserves explicit core flags;
scoring never changes curated files or infers core from mainChampion or style.
