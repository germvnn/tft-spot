# TFT Academy Data

## Snapshot

Set 18 raw files are stored directly under `data/raw/tft_academy`: comps.html,
augments.json, traits.json, champions.json, items.json, and manifest.json. Per-composition
responses and their index are stored under `data/raw/tft_academy/compositions`.

UI assets are stored separately under `data/assets`. Their manifest preserves
the owning entity source id and apiName, source field and URL, HTTP metadata, byte
size, SHA-256 digest, and download timestamp. Asset bytes are stored unchanged.
TFT Academy file URLs use collectionId, record id, and the source filename:
https://api.tftacademy.com/api/files/{collectionId}/{id}/{filename}.

The complete snapshot is reproducible with
`python scripts/download_tft_academy.py`. The downloader discovers visible
composition routes from the listing HTML, stores each route's SvelteKit data
response, downloads entity resources and UI assets, and writes provenance manifests.

Compositions come from the SvelteKit hydration payload in GET https://tftacademy.com/tierlist/comps, observed at data[2].data.guides. The current snapshot has 48 guides and 48 unique guide.id values but 47 unique compSlug values. Use guide.id as sourceId.

Counts: 260 augments, 36 traits, 72 champions, 139 items. Seven champions cost 0 and must remain.

## Relations

Use apiName for composition-to-champion, item, and augment references. Champion.traits contains Trait.id values and must resolve through Trait.id to Trait.apiName; traitContributions keys already use Trait.apiName. Item composition contains component Item.apiName values; preserve duplicates.

Validate all composition, champion-trait, trait-contribution, and item-component references. Broken references must produce explicit errors.

## Normalization Rules

1. Never modify raw files.
2. Extract guides from the SvelteKit payload and test the parser with a controlled fixture.
3. Preserve TFT Academy id as sourceId.
4. Use apiName for relations.
5. Preserve array order and duplicate components.
6. Do not filter non-public comps, tier X, or cost-0 champions.
7. Preserve description markup.
8. Treat null, empty string, and missing fields distinctly.
9. Do not infer business meaning from carousel or augmentTypes ordering.
