# TFT Spot Configurator

Local React, TypeScript, Vite, and Tailwind CSS interface for turning immutable
TFT Academy composition snapshots into reviewed `data/curated` configuration.

The UI expects the Python API at `http://127.0.0.1:8000`. Run it from the
repository root with:

```bash
uv run python -m tft_spot.configurator
pnpm --dir apps/configurator dev
```

Production verification:

```bash
pnpm --dir apps/configurator lint
pnpm --dir apps/configurator build
```
