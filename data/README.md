# Data layout

`data` is the single project-level home for datasets and UI assets. Data files do
not belong inside the `tft_spot` Python package.

```text
data/
├── assets/                     # locally stored UI images
│   ├── augments/
│   ├── champion_abilities/
│   ├── champions/
│   ├── items/
│   ├── traits/
│   └── manifest.json
└── raw/
    └── tft_academy/            # immutable source snapshots
        ├── compositions/       # per-composition responses and index.json
        ├── augments.json
        ├── champions.json
        ├── comps.html
        ├── items.json
        ├── manifest.json
        └── traits.json
```

Rebuild the complete local snapshot from the repository root:

```bash
python scripts/download_tft_academy.py
```

Downloaded data is excluded from Git. Only this README remains tracked. Use
`--skip-assets` to refresh raw resources and compositions without downloading
images.

Future normalized and curated datasets should also live under `data`, next to
`raw`, while Python code that reads or transforms them remains under `src`.
