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
version-controlled input for the future engine compiler.
