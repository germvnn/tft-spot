# TFT Spot Roadmap

## Phase 1 - Data Gathering and Normalization

### Data Gathering

- [x] Identify and fetch composition, augment, trait, champion, and item sources
- [x] Store raw snapshot
- [x] Analyze schemas and relationships
- [x] Verify composition references
- [x] Fetch champion, ability, item, augment, and trait UI assets
- [x] Make the complete local snapshot reproducible with one Python script

### Normalization

- [ ] Implement SvelteKit composition payload extractor
- [ ] Add composition parser fixture test
- [ ] Normalize compositions, champions, items, augments, and traits
- [ ] Convert champion trait IDs to Trait.apiName
- [ ] Validate champion, item, augment, and trait references
- [ ] Produce normalized Set 18 snapshot

Phase 1 exits when fetching is reproducible, extraction is reliable, normalized datasets are generated, integrity passes, and no scoring interpretation is required.

## Phase 2 - MVP Scoring Engine

Define models and semantics, then implement explainable component, augment, unit, and combined fit and ranking.

## Phase 3 - MVP Application

Expose data and recommendations through a backend and build the game-state configurator and explainable ranking UI.

## Later

Stage, economy, level, board strength, contested comps, scouting, positioning, transitions, automatic detection, statistics, and patch-aware models.
