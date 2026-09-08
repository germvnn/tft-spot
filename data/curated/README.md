# Curated composition configuration

The configurator stores one reviewed file per TFT Academy source guide:

```text
data/curated/set-<set>/compositions/<sourceId>.json
```

Curated files contain manual decisions only. Names, descriptions, board positions,
recommended items, and image filenames remain in the immutable raw snapshot and
are resolved through `apiName` while editing or compiling engine input.

## Contract

- `schemaVersion` is currently `1`.
- `sourceId` is the original TFT Academy guide id.
- `weights.units + weights.components + weights.augments` must equal `100`.
- priorities are `unset`, `essential`, `high`, `medium`, `low`, or `avoid`.
- `status: ready` requires all component/augment priorities to be set.
- entity references always use the source `apiName`.
- component priorities default to `essential` (Core); augment priorities default to `medium`.
- `earlyComp` units and star levels are resolved from the immutable raw snapshot.
  `units` stores per-apiName priorities; older configurations default to `medium`.
  Unit decisions also carry `core: false` by default. Save and bootstrap preserve
  explicit core flags. Core controls the unit-scoring share; legacy unit priority
  is retained for compatibility but no longer affects scoring or readiness.
- At most one augment can be `essential`: selecting it is required for eligibility.
  Unit/component `essential` is a preference. Ready saves cover all candidates.
- `finalComp` is reference-only.

The batch bootstrap follows source composition order, preserves existing non-`unset`
manual decisions, fills missing decisions with the defaults above, marks every
configuration as `ready`, and saves one file per `sourceId`.

Saving is atomic per composition: the API validates the full file, writes a temporary
sibling, and then replaces the target JSON. The batch action is safe to rerun.
