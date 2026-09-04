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
- `status: ready` is valid only when every priority is set.
- entity references always use the source `apiName`.
- component priorities default to `high`; augment priorities default to `medium`.
- `earlyComp` units and star levels are resolved directly from the immutable raw
  snapshot and do not have manual per-unit priorities.
- `finalComp` is reference-only.

Saving is atomic: the API validates the full file, writes a temporary sibling, and
then replaces the target JSON.
