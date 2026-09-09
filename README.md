# TFT Spot

TFT Spot recommends which Teamfight Tactics composition best fits the player's
current components, augments, and units.

## Download TFT Academy data

The downloaded dataset is reproducible and intentionally excluded from Git.
From the repository root, run:

```bash
python scripts/download_tft_academy.py
```

This downloads the current Set 18 snapshot into `data/`:

- TFT Academy composition listing and asset API responses,
- every visible composition's SvelteKit response,
- champion, ability, item, augment, and trait images,
- raw-data, composition, and asset manifests with hashes and source URLs.

Pass `--skip-assets` for a faster raw-data-only refresh. Run the command with
`--help` to see destination, set, retry, timeout, and concurrency options.

The Configurator's **Odśwież snapshot** action runs the same full download into
a temporary directory. It validates every guide before replacing the live raw
data and assets, then reconciles curated configurations. New compositions are
created as `ready`, settings for unchanged apiNames are preserved, obsolete
decisions are removed, and curated files whose composition disappeared from the
source are deleted. A failed download leaves the active snapshot untouched.

## Composition configurator

Install dependencies once:

```bash
uv sync
pnpm --dir apps/configurator install
```

Start the local API in the first terminal:

```bash
uv run python -m tft_spot.configurator
```

Start the React/Tailwind UI in the second terminal:

```bash
pnpm --dir apps/configurator dev
```

Open [http://127.0.0.1:5173](http://127.0.0.1:5173). The configurator reads
immutable TFT Academy snapshots from `data/raw`, serves downloaded images from
`data/assets`, and saves validated decisions to
`data/curated/set-18/compositions/<sourceId>.json`.

Raw snapshots and downloaded assets stay ignored. Curated configurations are
version-controlled input for the engine compiler.

The same API serves `POST /api/recommendations` for stage 2-1 direction matching.
See [scoring rules and request example](docs/SCORING.md). Early-unit priorities are
editable in the configurator; existing files default to medium until saved.

## Player interface

Open the same local UI at http://127.0.0.1:5173. Recommendations is the default
view; Configurator is a separate tab for setup and patch changes. Select cost 1-3
units and loose components with left-click (+1) or right-click (-1). Unit counts
are total copies, so a 2-star unit contributes three. Select the augment rarity
and up to three offered augments, then choose **Pokaż rekomendacje**. The ranking
appears below with images, the suggested augment and score contributions.

The two tabs retain input when switching; reloading the page starts a fresh spot.
The API must be restarted after updating backend code if it was launched without
reload. The documented `python -m tft_spot.configurator` entry point enables reload.

Browser regression tests (once dependencies and Chromium are installed):

```bash
pnpm --dir apps/configurator exec playwright install --with-deps chromium
pnpm --dir apps/configurator test:e2e
```

These tests run an isolated frontend on port 5174 with controlled API fixtures;
they do not modify curated configurations or require the raw snapshot.

## Simulator

Open the **Symulator** tab to generate 50 seeded opener cases and rate individual
composition results. Saved runs and human reviews survive refresh. Use **Przelicz
te same spoty** after tuning the engine to compare the same inputs, or **Eksport
JSON** to download the evaluation dataset. See [simulator details](docs/SIMULATOR.md).
