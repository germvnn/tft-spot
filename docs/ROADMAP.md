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
- [x] Bootstrap all curated composition configurations with explicit defaults

Phase 1 exits when fetching is reproducible, extraction is reliable, normalized datasets are generated, integrity passes, and no scoring interpretation is required.

## Phase 2 - MVP Scoring Engine

- [x] Define stage 2-1 spot and compiled composition contracts
- [x] Add curated early-unit priorities and single-essential-augment validation
- [x] Implement explained component, augment, Fibonacci unit and combined matching
- [x] Rank composition/augment scenarios with explicit eligibility
- [x] Expose POST /api/recommendations
- [x] Group same-name/tier augment choices and resolve all apiName aliases in matching
- [x] Store optional per-unit core flags, default false, without blocking batch saves
- [ ] Calibrate matching scores against representative player-reviewed spots
- [x] Replace the 21-point unit normalization with core shares and a four-copy cap
- [x] Cover the Veigar four-copy/three-support example (37.5/40) and multiple core units

- [x] Add presence baseline for no-core openers (Veigar example: 28.75/40)
- [x] Generate reproducible 50-case calibration runs, human reviews and replay

## Phase 3 - MVP Application

- [x] Separate Recommendations and Configurator tabs; open Recommendations by default
- [x] Add stage 2-1 inventory entry with left/right click quantity controls
- [x] Show cost 1-3 units with gray/green/blue borders
- [x] Select up to three offered augments through silver/gold/prismatic filtering
- [x] Display ranked compositions, champion images, suggested augment and explanations
- [x] Cover refresh, legacy configuration, counters, rarity and mobile layout in browser tests

- [x] Add Simulator tab with per-case reviews, saved runs and JSON export

## Later

Stage, economy, level, board strength, contested comps, scouting, positioning, transitions, automatic detection, statistics, and patch-aware models.

- [x] Simulator openers-v2: unique components with calibrated batch proportions, 7-14 gold of units, maximum four copies and displayed inventory cost.
