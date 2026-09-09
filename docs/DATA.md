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

The local composition index used for the v3 audit contains 24 entries (all ready);
this differs from the earlier 48-guide listing snapshot described above. The
benchmark reports actual local coverage; it does not silently equate both sets.
