# TFT Academy Data

## Snapshot

Set 18 raw files are stored directly under `data/raw/tft_academy`: comps.html,
augments.json, traits.json, champions.json, items.json, and manifest.json. The raw
SvelteKit guide collection is stored unchanged as `compositions/guides.json`; its
derived index is stored alongside it.

UI assets are stored separately under `data/assets`. Their manifest preserves
the owning entity source id and apiName, source field and URL, HTTP metadata, byte
size, SHA-256 digest, and download timestamp. Asset bytes are stored unchanged.
TFT Academy file URLs use collectionId, record id, and the source filename:
https://api.tftacademy.com/api/files/{collectionId}/{id}/{filename}.

The complete snapshot is reproducible with
`python scripts/download_tft_academy.py`. The downloader fetches
`/tierlist/comps/__data.json` once and indexes every guide whose explicit `set`
matches the requested set, in source array order. This includes sidebar variants,
non-public guides and tier-X entries. Each index entry uses `guide.id` as its
sourceId and may share or omit `compSlug`; slugs are not identity. Entity resources
and UI assets are downloaded separately and provenance manifests include the
unchanged guide payload.

Configurator source refreshes are staged under a temporary project directory.
The staged raw snapshot is parsed and all composition references are resolved
before raw data, assets, and the active set's curated composition directory are
swapped into place. Existing decisions are retained by apiName, source order is
rebuilt from the new guide, new decisions receive explicit defaults, and new
compositions become ready. Curated files are deleted only for sourceIds present
in the previous index and absent from the refreshed complete guide collection.
Legacy composition indexes may omit their top-level set field. Refresh resolves
that compatibility case from the explicit guide.set values and requires every
guide to agree; it never infers a set number from route slugs.

Compositions come from the SvelteKit hydration payload in GET
https://tftacademy.com/tierlist/comps/__data.json, observed in a decoded `guides`
node. On 2026-09-09 the Set 18 response had 53 guides, 53 unique `guide.id` values
and 52 unique `compSlug` values: 35 guides were public and 18 non-public. Two
guides had an empty slug. Use `guide.id` as sourceId.

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

## Stage 2-1 engine adapter

The engine compiler currently uses the configurator's resolved per-composition
workspace. It carries guide sourceId, set, explicit curated priorities, distinct
early-unit apiNames and component requiredCount into validated engine models.
Raw earlyComp star levels remain reference-only. Component capacity is an explicit
MVP interpretation of the existing recipe tally; source carousel ordering never
sets priorities. See SCORING.md for the full scoring and compatibility contract.

## Player catalog presentation

GET /api/spot-catalog exposes sourceId, apiName, setNumber and local image URLs.
Champion cost comes directly from raw cost. All champions remain in this response;
the player picker shows only costs 1, 2 and 3. Augment tier is numeric in the local
snapshot: 1 = silver, 2 = gold, 3 = prismatic. Source stages and disabled metadata
are preserved. Components are entries whose raw type equals components.
Recommendation responses add mainChampion, finalUnits, tier and style for display;
these fields do not alter matching scores.

## Augment equivalence for matching

The local snapshot contains 260 source augment records but 251 distinct
(set, tier, name) groups. Gold Consuming Flora has three apiNames for stages
2-1, 3-2 and 4-2. Unrivaled, Sun and Moon, Beast Within and Nesting Dolls also
have same-name/tier variants. The player selector presents one group entry,
retaining aliasApiNames and each variant's sourceId, stages, description and
disabled metadata. Grouping is exact by name and tier within a set, not fuzzy.
The first source occurrence is the representative apiName. All source records
and curated apiName references remain unchanged on disk. The compiler and API
resolve those references and offered aliases to the same representative.

## Role and item audit (2026-09-08)

The local champion snapshot has explicit `role` strings, separate from traits.
Observed counts include 7 Attack Casters, 5 Attack Marksmen, 13 Magic Casters,
2 Magic Marksmen and 4 empty roles. Roles are exposed without filling empty
values. Specialist/unknown roles receive no inferred role-item affinity.

Craftable recipes use component apiNames, including repeated components (Red
Buff uses two bows). Shojin's local description grants bonus mana on attacks;
Last Whisper applies Sunder through attacks and ability damage; Red Buff applies
Burn/Wound; Guinsoo stacks attack speed over time. These are distinct functions,
not exclusive item classes. Local item stats/descriptions contain missing values
and suspicious text (e.g. Nashor's critical-attack mana clause); the engine does
not parse descriptions into numerical combat models. `filterType` and
`recommendedChampions` are not interpreted as score weights. The latter can
contain champion source ids and is not used for apiName matching.

Role priors live in engine/item_fit.py, scoped to Set 18 and versioned separately.
They are domain annotations, not normalized facts. Explicit per-champion
exceptions override source early/final assigned items, which override role
priors. Carousel order is never used to derive these affinities. Raw files and
existing curated composition files are not migrated by this change.

The local composition index used for the v3 audit contained 24 ready entries.
That was a historical audit input and is smaller than the complete current guide
collection. The benchmark reports actual local coverage; it does not silently
equate the two datasets.


## Curated rule retirement during refresh

Configurations may include retiredStrategyRules (default empty). Each archived
entry contains kind, the original rule in camelCase, and a validation reason.
Refresh archives invalid openers, item overrides and augment conditions instead
of discarding manual annotations or rejecting the entire snapshot. An opener
with an invalid unit is archived as a whole so refresh cannot silently redefine
its composition. Affected configurations become draft; valid rules and previous
archives are preserved. This is curated metadata and does not change raw records.

Ranking and simulation now load the shared guide payload once per operation.
The returned workspace and scoring inputs keep source order and existing
transformations; no normalized snapshot or new scoring semantics are introduced.
