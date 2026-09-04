# TFT Spot - Agent Guidelines

Read docs/PROJECT.md, docs/DATA.md, docs/DECISIONS.md, and docs/ROADMAP.md before architectural or domain work.

Current phase: Phase 1 - Data Gathering and Normalization. Do not implement scoring unless explicitly requested.

Use apiName for cross-entity relations, preserve source id as sourceId, and use composition guide.id rather than compSlug as the source identifier. Preserve raw data, source array order, duplicate components, null/empty/missing distinctions, non-public and tier-X compositions, and cost-0 champions. Do not infer scoring semantics from carousel or augmentTypes.

Prefer straightforward Python and explicit transformations. Avoid unnecessary databases, microservices, ML/LLM scoring, repositories, factories, and abstractions. Update DATA for source discoveries, DECISIONS for meaningful decisions, and ROADMAP for completed milestones.
