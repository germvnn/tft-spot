# TFT Spot - Architecture and Domain Decisions

- ADR-001 (Accepted): raw source data is immutable.
- ADR-002 (Accepted): use apiName as the integration identifier.
- ADR-003 (Accepted): preserve TFT Academy IDs as sourceId.
- ADR-004 (Accepted): Composition.sourceId is guide.id, not compSlug.
- ADR-005 (Accepted): separate raw, normalized, and scoring concerns.
- ADR-006 (Accepted): do not filter during normalization.
- ADR-007 (Accepted): preserve source array order.
- ADR-008 (Accepted): do not infer carousel semantics yet.
- ADR-009 (Accepted): do not infer augmentTypes scoring semantics yet.
- ADR-010 (Accepted): MVP scoring has component, augment, and unit dimensions.
- ADR-011 (Accepted): keep architecture intentionally simple.
- ADR-012 (Accepted): keep source snapshots under `data/raw/<source>` and UI assets
  under `data/assets`; application data must not live inside the Python package.
- ADR-013 (Accepted): downloaded data is reproducible, excluded from Git, and
  generated with one standard-library Python command.
