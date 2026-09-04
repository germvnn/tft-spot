# TFT Spot

TFT Spot recommends which Teamfight Tactics composition best fits the player's
current components, augments, and units.

## Download TFT Academy data

The complete local dataset is reproducible and intentionally excluded from Git.
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
