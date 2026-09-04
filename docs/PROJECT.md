# TFT Spot

TFT Spot is a Teamfight Tactics decision-support application answering: Given my current spot, which composition should I play?

The MVP eventually evaluates component fit, augment fit, and unit fit with explainable scores. First understand and preserve TFT Academy data, normalize it into a stable domain-ready representation, then define scoring.

Data flow: TFT Academy -> raw data -> normalization -> domain-ready data -> scoring engine -> API -> UI.

Raw data contains no business interpretation. Normalization extracts compositions, resolves identifiers to apiName, creates predictable structures, and validates referential integrity.

Out of scope initially: ML/LLM scoring, economy and stage evaluation, scouting, contested comps, positioning, combat simulation, and automatic game-state reading.
