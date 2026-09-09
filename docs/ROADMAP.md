# TFT Spot Roadmap

## Phase 1 - Data Gathering and Normalization

### Data Gathering

- [x] Identify and fetch composition, augment, trait, champion, and item sources
- [x] Store raw snapshot
- [x] Analyze schemas and relationships
- [x] Verify composition references
- [x] Fetch champion, ability, item, augment, and trait UI assets
- [x] Make the complete local snapshot reproducible with one Python script
- [x] Discover sidebar variants, non-public guides, and tier-X entries
- [x] Refresh and reconcile the complete snapshot from the Configurator UI

### Normalization

- [x] Implement SvelteKit composition payload extractor
- [x] Add composition parser fixture test
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


## Research-driven stage 2-1 refinement (2026-09-08)

- [x] Audit champion roles and item semantics against local data and Riot's role documentation
- [x] Add versioned role priors, explicit item overrides and non-overlapping item plans
- [x] Add configurable augment conditions and alternative openers with UI editing
- [x] Distinguish unassessed augment choices from hard eligibility blocks
- [x] Explain item holders, source/role evidence and component-score contribution
- [x] Add opt-in broad composition coverage with duplicate-component stress cases
- [x] Save acceptable top-3 directions and separate calibration/holdout labels
- [x] Replay the two pre-existing 50-case runs and add a reproducible evaluation command
- [ ] Curate alternative openers and augment conditions for individual compositions
- [ ] Validate role priors and the 25% item-plan blend with player-reviewed cases
- [ ] Collect real 2-1 inputs for independent validation (synthetic cases are not substitutes)


## Reliability refactor (2026-09-09)

- [x] Share the standard-library SvelteKit parser between downloader and application
- [x] Load each raw source file once per ranking/simulation/batch operation
- [x] Separate source presentation, expert-rule validation and configurator state
- [x] Validate equivalent augment priorities before writing configurations
- [x] Preserve edits made while saving and ignore stale workspace responses
- [x] Preserve reference labels through repeated simulator replays
- [x] Serialize API data readers with source refresh and configuration writes
- [x] Archive orphaned expert rules during refresh and mark affected configurations draft
- [x] Add backend and browser regressions for review findings
