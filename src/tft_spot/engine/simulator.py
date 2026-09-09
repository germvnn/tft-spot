"""Seeded calibration cases, frozen results, and separately saved human reviews."""

from __future__ import annotations

import hashlib
import json
import random
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import Field

from tft_spot.configurator.presentation import entity_card
from tft_spot.configurator.repository import ConfigurationRepository
from tft_spot.data.augment_identity import build_augment_aliases
from tft_spot.engine.compiler import compile_workspace
from tft_spot.engine.scoring import SCORING_VERSION, rank_compositions
from tft_spot.models.configuration import ApiModel
from tft_spot.models.spot import OwnedComponent, OwnedUnit, Spot

GENERATOR_VERSION = "openers-v2"
PATTERNS = [
    "solo_four",
    "all_singles",
    "two_pairs",
    "four_plus_support",
    "two_star_plus_support",
    "sparse_pair",
    "off_direction",
    "component_mismatch",
    "missing_core_augment",
    "mixed_opener",
]
LABELS = [
    "Jednostka x4 + pozostały zakup",
    "Pełny opener po jednej kopii",
    "Dwie pary",
    "Cztery kopie + wsparcie",
    "Jednostka 2★ + wsparcie",
    "Para + pozostały zakup",
    "Jednostki innego kierunku",
    "Słabe komponenty",
    "Oferta bez wymaganego augmentu",
    "Mieszany opener",
]


class SimulationRequest(ApiModel):
    set_number: int = Field(default=18, ge=1, strict=True)
    count: int = Field(default=50, ge=1, le=200, strict=True)
    seed: int = Field(default=42, ge=0, le=2**31 - 1, strict=True)
    source_id: str | None = None
    mode: Literal["standard", "coverage"] = "standard"


class Review(ApiModel):
    source_id: str = Field(min_length=1)
    verdict: Literal["too_low", "about_right", "too_high", "unrealistic"]
    expected_unit_fit: float | None = Field(default=None, ge=0, le=100)
    expected_score: float | None = Field(default=None, ge=0, le=100)
    acceptable_source_ids: list[str] = Field(default_factory=list, max_length=48)
    split: Literal["calibration", "holdout"] = "calibration"
    notes: str = Field(default="", max_length=4000)


def _directory(root: Path) -> Path:
    return root / "data" / "evaluations" / "simulator"


def _id(run_id: str) -> str:
    return str(UUID(run_id))


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid4().hex + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def load_run(root: Path, run_id: str) -> dict[str, Any]:
    run_id = _id(run_id)
    run = json.loads((_directory(root) / f"{run_id}.json").read_text(encoding="utf-8"))
    for case in run["cases"]:
        review_file = _directory(root) / "reviews" / run_id / f"{case['id']}.json"
        case["review"] = (
            json.loads(review_file.read_text(encoding="utf-8"))
            if review_file.exists()
            else None
        )
    run["benchmark"] = benchmark_summary(run["cases"])
    return run


def list_runs(root: Path) -> list[dict[str, Any]]:
    result = []
    for path in sorted(
        _directory(root).glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True
    ):
        run = json.loads(path.read_text(encoding="utf-8"))
        result.append(
            {
                key: run[key]
                for key in (
                    "id",
                    "createdAt",
                    "scoringVersion",
                    "seed",
                    "count",
                    "setNumber",
                )
            }
        )
    return result


def save_review(
    root: Path, run_id: str, case_id: int, review: Review
) -> dict[str, Any]:
    run = load_run(root, run_id)
    case = next((case for case in run["cases"] if case["id"] == case_id), None)
    if case is None:
        raise ValueError("Unknown simulation case")
    if review.source_id not in {r["sourceId"] for r in case["rankings"]}:
        raise ValueError("Reviewed composition is not in this case")
    if not set(review.acceptable_source_ids) <= {
        r["sourceId"] for r in case["rankings"]
    }:
        raise ValueError("Unknown acceptable composition")
    saved = {**review.model_dump(), "updatedAt": datetime.now(UTC).isoformat()}
    _write(_directory(root) / "reviews" / _id(run_id) / f"{case_id}.json", saved)
    return saved


def _component_schedule(rng: random.Random, count: int) -> list[int]:
    # Largest remainder allocation; seeded ties avoid favoring either 5% bucket.
    weights = {1: 1, 2: 1, 3: 16, 5: 2}
    allocated = {size: count * weight // 20 for size, weight in weights.items()}
    order = list(weights)
    rng.shuffle(order)
    order.sort(key=lambda size: count * weights[size] % 20, reverse=True)
    for size in order[: count - sum(allocated.values())]:
        allocated[size] += 1
    schedule = [size for size, number in allocated.items() for _ in range(number)]
    rng.shuffle(schedule)
    return schedule


def _budget_units(
    rng: random.Random,
    owned: dict[str, int],
    costs: dict[str, int],
    target_names: list[str],
    anchor: str,
) -> dict[str, int]:
    owned = dict(owned)
    budget = max(rng.randint(7, 14), owned.get(anchor, 0) * costs[anchor])
    total = sum(costs[name] * count for name, count in owned.items())
    while total > budget:
        choices = [name for name in owned if name != anchor] or list(owned)
        name = rng.choice(choices)
        owned[name] -= 1
        total -= costs[name]
        if not owned[name]:
            del owned[name]
    while total < budget:
        ceiling = budget if total >= 7 else max(budget, 9)
        choices = [
            name
            for name, cost in costs.items()
            if owned.get(name, 0) < 4 and cost <= ceiling - total
        ]
        if not choices:
            break
        # Fill the economic budget without artificially strengthening the target.
        outsiders = [name for name in choices if name not in target_names]
        name = rng.choice(outsiders or choices)
        owned[name] = owned.get(name, 0) + 1
        total += costs[name]
    if not 7 <= total <= 14:
        raise ValueError("Insufficient unit catalog for a 7-14 gold opener")
    return owned


def generate_run(
    root: Path, options: SimulationRequest, previous: dict[str, Any] | None = None
) -> dict[str, Any]:
    repo = ConfigurationRepository(root)
    snapshot = repo.load_snapshot()
    catalogs = snapshot.catalogs
    aliases = build_augment_aliases(catalogs["augments"])
    workspaces = [
        repo.get_workspace(c["sourceId"], snapshot=snapshot)
        for c in repo.list_compositions(snapshot)
    ]
    workspaces = [
        w
        for w in workspaces
        if w["source"]["set"] == options.set_number
        and w["configuration"]["status"] == "ready"
    ]
    compiled = [compile_workspace(w, aliases, catalogs) for w in workspaces]
    if not compiled:
        raise ValueError("No ready compositions for this set")
    eligible_units = {
        name: c
        for name, c in catalogs["champions"].items()
        if c.get("set") == options.set_number and c.get("cost") in (1, 2, 3)
    }
    components = [
        name
        for name, c in catalogs["items"].items()
        if c.get("set") == options.set_number and c.get("type") == "components"
    ]
    # Only known stage-2-1 variants can enter the generated offer, never later-only ones.
    augments = list(
        dict.fromkeys(
            aliases[name]
            for name, a in catalogs["augments"].items()
            if a.get("set") == options.set_number
            and "2-1" in (a.get("stages") or [])
            and not a.get("disabled")
        )
    )
    if not eligible_units or not components or not augments:
        raise ValueError("Insufficient stage 2-1 catalog data for simulation")
    by_id = {c.source_id: c for c in compiled}
    mains = {
        w["source"]["sourceId"]: (w["source"].get("mainChampion") or {}).get("apiName")
        for w in workspaces
    }
    targets = [
        c
        for c in compiled
        if any(u.api_name in eligible_units for u in c.units)
        and (options.source_id is None or c.source_id == options.source_id)
    ]
    if not targets:
        raise ValueError("No matching ready opener for simulation")
    rng = random.Random(options.seed)
    rng.shuffle(targets)
    component_schedule = _component_schedule(rng, options.count) if not previous else []
    if not previous and len(components) < max(component_schedule):
        raise ValueError("Insufficient distinct components for simulation")
    costs = {name: c["cost"] for name, c in eligible_units.items()}
    display = {}
    for category, fields in (
        ("champions", ("championSquareIcon", "championIcon")),
        ("items", ("icon",)),
        ("augments", ("icon",)),
    ):
        for name, entity in catalogs[category].items():
            display[name] = entity_card(entity, category, fields)
    cases = []
    source_cases = previous["cases"] if previous else [None] * options.count
    for index, old_case in enumerate(source_cases):
        target = targets[
            (index if options.mode == "coverage" else index // len(PATTERNS))
            % len(targets)
        ]
        pattern = index % len(PATTERNS)
        if old_case:
            spot = Spot.model_validate(old_case["spot"])
            for unit in spot.units:
                if unit.api_name not in catalogs["champions"]:
                    raise ValueError(f"Replay has unknown unit: {unit.api_name}")
            for component in spot.components:
                if component.api_name not in components:
                    raise ValueError(
                        f"Replay has unknown component: {component.api_name}"
                    )
            if any(name not in aliases for name in spot.offered_augments):
                raise ValueError("Replay has unknown augment")
            spot = Spot.model_validate(
                {
                    **spot.model_dump(),
                    "offeredAugments": [
                        aliases[name] for name in spot.offered_augments
                    ],
                }
            )
            target_id = old_case["targetSourceId"]
        else:
            names = [u.api_name for u in target.units if u.api_name in eligible_units]
            core = [
                u.api_name
                for u in target.units
                if u.core and u.api_name in eligible_units
            ]
            anchor = (
                core[0]
                if core
                else next(
                    (name for name in names if name == mains.get(target.source_id)),
                    names[0],
                )
            )
            owned = {name: 1 for name in names[:4]}
            owned[anchor] = 1
            if pattern == 0:
                owned = {anchor: 4}
            elif pattern == 2:
                owned = {name: 2 for name in names[:2]}
            elif pattern in (3, 7, 8):
                owned[anchor] = 4
            elif pattern == 4:
                owned[anchor] = 3
            elif pattern == 5:
                owned = {anchor: 2}
            elif pattern == 6:
                outsiders = [name for name in eligible_units if name not in names]
                owned = {
                    name: 1 for name in rng.sample(outsiders, min(4, len(outsiders)))
                }
            elif pattern == 9:
                owned = {
                    name: rng.randint(1, 3)
                    for name in rng.sample(
                        list(eligible_units), min(4, len(eligible_units))
                    )
                }
            owned = _budget_units(rng, owned, costs, names, anchor)
            preferred = [
                a.api_name
                for a in target.augments
                if a.api_name in augments and a.priority not in ("avoid", "unset")
            ]
            required = next(
                (a.api_name for a in target.augments if a.priority == "essential"), None
            )
            anchor_augment = (
                required
                if required in preferred
                else (preferred[0] if preferred else rng.choice(augments))
            )
            if pattern == 8:
                choices = [name for name in augments if name != required]
                if choices:
                    anchor_augment = rng.choice(choices)
            tier = catalogs["augments"][anchor_augment]["tier"]
            pool = [
                name
                for name in augments
                if catalogs["augments"][name]["tier"] == tier
                and name != anchor_augment
                and (pattern != 8 or name != required)
            ]
            offers = [anchor_augment, *rng.sample(pool, min(2, len(pool)))]
            rng.shuffle(offers)
            preferred_components = [
                c.api_name
                for c in target.components
                if c.api_name in components and c.priority not in ("avoid", "unset")
            ]
            pool_components = (
                [name for name in components if name not in preferred_components]
                if pattern == 7
                else preferred_components
            )
            pool_components = pool_components or components
            pool_components = list(dict.fromkeys(pool_components))
            amount = component_schedule[index]
            selected_components = rng.sample(
                pool_components, min(amount, len(pool_components))
            )
            remaining = [name for name in components if name not in selected_components]
            selected_components.extend(
                rng.sample(remaining, amount - len(selected_components))
            )
            if options.mode == "coverage" and amount >= 2:
                # Explicit stress sample, not a claim about real drop frequencies.
                selected_components[-1] = selected_components[0]
            component_counts = {
                n: selected_components.count(n)
                for n in dict.fromkeys(selected_components)
            }
            spot = Spot(
                set_number=options.set_number,
                offered_augments=offers,
                units=[
                    OwnedUnit(api_name=name, count=count)
                    for name, count in owned.items()
                ],
                components=[
                    OwnedComponent(api_name=name, count=count)
                    for name, count in component_counts.items()
                ],
            )
            target_id = target.source_id
        rankings = rank_compositions(compiled, spot)
        cases.append(
            {
                "id": index + 1,
                "pattern": old_case["pattern"] if old_case else PATTERNS[pattern],
                "label": old_case["label"]
                if old_case
                else (
                    "Alternatywna oferta augmentów"
                    if pattern == 8 and not required
                    else LABELS[pattern]
                ),
                "targetSourceId": target_id,
                "targetTitle": by_id[target_id].title
                if target_id in by_id
                else old_case["targetTitle"],
                "unitGold": sum(
                    catalogs["champions"][u.api_name]["cost"] * u.count
                    for u in spot.units
                ),
                "spot": spot.model_dump(),
                "rankings": rankings,
                "review": None,
                "referenceReview": (
                    old_case.get("review") or old_case.get("referenceReview")
                )
                if old_case
                else None,
                "previousScores": {
                    r["sourceId"]: r["score"] for r in old_case["rankings"]
                }
                if old_case
                else None,
            }
        )
    frozen = [c.model_dump() for c in compiled]
    fingerprint = hashlib.sha256(
        json.dumps({"catalogs": catalogs, "compiled": frozen}, sort_keys=True).encode()
    ).hexdigest()
    run = {
        "id": str(uuid4()),
        "createdAt": datetime.now(UTC).isoformat(),
        "setNumber": options.set_number,
        "seed": options.seed,
        "count": len(cases),
        "scoringVersion": SCORING_VERSION,
        "generatorVersion": previous["generatorVersion"]
        if previous
        else ("coverage-v1" if options.mode == "coverage" else GENERATOR_VERSION),
        "mode": previous.get("mode", "standard") if previous else options.mode,
        "sourceId": options.source_id,
        "inputFingerprint": fingerprint,
        "compiledInputs": frozen,
        "parentRunId": previous["id"] if previous else None,
        "entities": display,
        "benchmark": benchmark_summary(cases),
        "compositionBoards": (
            previous.get("compositionBoards", {})
            if previous
            else {w["source"]["sourceId"]: w["finalUnits"] for w in workspaces}
        ),
        "cases": cases,
    }
    _write(_directory(root) / f"{run['id']}.json", run)
    return run


def benchmark_summary(cases: list[dict]) -> dict:
    result: dict[str, Any] = {}
    for split in ("calibration", "holdout"):
        reviewed = hits = 0
        for case in cases:
            review = case.get("review") or case.get("referenceReview")
            if (
                not review
                or review.get("split", "calibration") != split
                or review.get("verdict") == "unrealistic"
            ):
                continue
            accepted = set(review.get("acceptableSourceIds", []))
            if not accepted:
                continue
            reviewed += 1
            top = [r["sourceId"] for r in case["rankings"] if r["eligible"]][:3]
            hits += bool(accepted.intersection(top))
        result[split] = {
            "reviewedCases": reviewed,
            "top3Hits": hits,
            "top3HitRate": hits / reviewed if reviewed else None,
        }
    result["targetCoverage"] = len({c["targetSourceId"] for c in cases})
    result["duplicateComponentCases"] = sum(
        any(c["count"] > 1 for c in case["spot"]["components"]) for case in cases
    )
    return result
