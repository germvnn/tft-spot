"""Small, versioned role priors and an exact non-overlapping item allocation.

Role priors are hypotheses, not BIS lists. Explicit champion annotations override
source builds, which override these priors. No source arrays imply priority.
"""

from collections import Counter
from functools import cache
from typing import Any

ROLE_PROFILE_VERSION = "set18-roles-v1"
ROLE_SOURCE = "https://teamfighttactics.leagueoflegends.com/en-us/news/game-updates/roles-revamped-and-item-changes/"
# Item apiNames refer to the local Set 18 snapshot; values are calibration priors.
ITEM_ROLES = {
    "DA_SpearOfShojin": ("mana", {"Attack Caster": 0.85, "Magic Caster": 0.85}),
    "DA_BlueBuff": ("mana", {"Attack Caster": 0.8, "Magic Caster": 0.8}),
    "DA_GuinsoosRageblade": (
        "attack_speed",
        {"Attack Marksman": 0.85, "Magic Marksman": 0.85},
    ),
    "DA_LastWhisper": ("sunder", {"Attack Caster": 0.75, "Attack Marksman": 0.75}),
    "DA_RedBuff": (
        "antiheal",
        {"Attack Caster": 0.6, "Attack Marksman": 0.75, "Magic Marksman": 0.6},
    ),
}


# Conservative defaults by job; offensive type remains separate from frontline role.
for item, category, roles in [
    (
        "DA_Deathblade",
        "attack_damage",
        {"Attack Caster": 0.7, "Attack Marksman": 0.7, "Attack Fighter": 0.6},
    ),
    (
        "DA_InfinityEdge",
        "spell_crit",
        {"Attack Caster": 0.75, "Attack Marksman": 0.65, "Attack Assassin": 0.7},
    ),
    ("DA_KrakensFury", "attack_damage", {"Attack Marksman": 0.8}),
    (
        "DA_RabadonsDeathcap",
        "ability_power",
        {"Magic Caster": 0.75, "Magic Marksman": 0.65},
    ),
    ("DA_JeweledGauntlet", "spell_crit", {"Magic Caster": 0.75, "Magic Fighter": 0.65}),
    ("DA_ArchangelsStaff", "ability_power", {"Magic Caster": 0.65}),
    ("DA_Morellonomicon", "antiheal", {"Magic Caster": 0.7}),
    ("DA_VoidStaff", "shred", {"Magic Caster": 0.7, "Magic Marksman": 0.7}),
    (
        "DA_Bloodthirster",
        "sustain",
        {
            "Attack Fighter": 0.8,
            "Magic Fighter": 0.75,
            "Attack Assassin": 0.65,
            "Magic Assassin": 0.65,
        },
    ),
    (
        "DA_HandOfJustice",
        "sustain",
        {
            "Attack Fighter": 0.7,
            "Magic Fighter": 0.7,
            "Attack Assassin": 0.7,
            "Magic Assassin": 0.7,
        },
    ),
    ("DA_TitansResolve", "fighter", {"Attack Fighter": 0.7, "Magic Fighter": 0.7}),
    ("DA_SteraksGage", "fighter", {"Attack Fighter": 0.75}),
]:
    ITEM_ROLES[item] = (category, roles)
for item, category in [
    ("DA_WarmogsArmor", "tank"),
    ("DA_BrambleVest", "tank"),
    ("DA_DragonsClaw", "tank"),
    ("DA_GargoyleStoneplate", "tank"),
    ("DA_SpiritVisage", "tank"),
    ("DA_SteadfastHeart", "tank"),
    ("DA_ProtectorsVow", "tank"),
    ("DA_SunfireCape", "antiheal"),
    ("DA_Evenshroud", "sunder"),
    ("DA_IonicSpark", "shred"),
]:
    ITEM_ROLES[item] = (category, {"Attack Tank": 0.7, "Magic Tank": 0.7})


def compile_item_context(workspace: dict, catalogs: dict) -> dict:
    """Freeze only inputs used by this composition so replay has its role evidence."""
    from tft_spot.models.configuration import StrategySettings

    settings = StrategySettings.model_validate(
        workspace["configuration"].get("strategy", {})
    )
    champions, items = catalogs["champions"], catalogs["items"]
    set_number = workspace["source"]["set"]
    overrides = {
        (o.champion_api_name, o.item_api_name): o for o in settings.item_overrides
    }
    explicit: dict[str, set[str]] = {}
    for unit in workspace.get("finalUnits", []) + workspace.get("earlyUnits", []):
        explicit.setdefault(unit["apiName"], set()).update(
            i["apiName"] for i in unit.get("items", [])
        )
    targets = list(dict.fromkeys(u["apiName"] for u in workspace.get("finalUnits", [])))
    holders = [
        n
        for n, c in champions.items()
        if c.get("set") == set_number and c.get("cost") in (1, 2, 3)
    ]

    def affinity(champion: str, item: str) -> tuple[float, str]:
        override = overrides.get((champion, item))
        if override:
            return override.fit, override.reason
        if item in explicit.get(champion, set()):
            return 1.0, "source_build"
        role = champions[champion].get("role")
        if set_number == 18:
            return ITEM_ROLES.get(item, ("", {}))[1].get(role, 0.0), "role_prior"
        return 0.0, "unassessed"

    options = []
    for name, item in items.items():
        recipe = item.get("composition")
        if (
            item.get("set") != set_number
            or item.get("type") != "craftables"
            or not recipe
            or len(recipe) != 2
        ):
            continue
        for component in recipe:
            if component not in items or items[component].get("type") != "components":
                raise ValueError(f"Invalid component recipe: {name}: {component}")
        target_fits = [(n, *affinity(n, name)) for n in targets]
        target_fits = [t for t in target_fits if t[1] > 0]
        if not target_fits:
            continue
        target, target_fit, target_basis = max(target_fits, key=lambda t: t[1])
        for holder in holders:
            fit, basis = affinity(holder, name)
            if fit <= 0:
                continue
            options.append(
                {
                    "itemApiName": name,
                    "itemName": item["name"],
                    "recipe": recipe,
                    "holderApiName": holder,
                    "holderName": champions[holder]["name"],
                    "holderRole": champions[holder].get("role"),
                    "holderFit": fit,
                    "holderBasis": basis,
                    "targetApiName": target,
                    "targetName": champions[target]["name"],
                    "targetFit": target_fit,
                    "targetBasis": target_basis,
                    "category": ITEM_ROLES.get(name, (name, {}))[0],
                }
            )
    return {"version": ROLE_PROFILE_VERSION, "source": ROLE_SOURCE, "options": options}


def allocate_items(context: dict, owned: Counter, copies: Counter) -> dict[str, Any]:
    # This stage-2-1 model handles up to five complete items. Larger manually
    # entered inventories use the unchanged component heuristic, explicitly.
    total = sum(owned.values())
    if not context.get("options"):
        return {
            "available": False,
            "reason": "no_item_evidence",
            "plans": [],
            "fit": None,
        }
    if total > 10:
        return {
            "available": False,
            "reason": "inventory_above_stage_2_1_limit",
            "plans": [],
            "fit": None,
        }
    names = sorted(owned)
    holders = sorted(n for n, count in copies.items() if count)
    options = []
    for option in context.get("options", []):
        if not copies[option["holderApiName"]]:
            continue
        recipe = Counter(option["recipe"])
        if any(owned[n] < count for n, count in recipe.items()):
            continue
        upgrade = 1.0 if copies[option["holderApiName"]] >= 3 else 0.65
        quality = option["targetFit"] * option["holderFit"] * upgrade
        options.append({**option, "quality": quality, "upgradedHolder": upgrade == 1})
    targets = sorted({o.get("targetApiName", o["holderApiName"]) for o in options})
    # Repeated utility effects do not create extra utility value across holders.
    utility = {"sunder": 1, "antiheal": 2, "shred": 4}

    @cache
    def solve(remaining: tuple, slots: tuple, mask: int):
        best = (0.0, ())
        for i, option in enumerate(options):
            holder_index = holders.index(option["holderApiName"])
            target_index = len(holders) + targets.index(
                option.get("targetApiName", option["holderApiName"])
            )
            bit = utility.get(option["category"], 0)
            if (
                slots[holder_index] >= 3
                or slots[target_index] >= 3
                or (bit and mask & bit)
            ):
                continue
            required = Counter(option["recipe"])
            if any(remaining[names.index(n)] < c for n, c in required.items()):
                continue
            next_remaining = tuple(c - required[n] for n, c in zip(names, remaining))
            next_slots = list(slots)
            next_slots[holder_index] += 1
            next_slots[target_index] += 1
            value, chosen = solve(next_remaining, tuple(next_slots), mask | bit)
            candidate = option["quality"] + value
            if candidate > best[0] + 1e-9:
                best = (candidate, (i, *chosen))
        return best

    value, selected = solve(
        tuple(owned[n] for n in names), (0,) * (len(holders) + len(targets)), 0
    )
    plans = [options[i] for i in selected]
    used = Counter(n for p in plans for n in p["recipe"])
    return {
        "available": True,
        "fit": 100 * value / (total // 2) if total >= 2 else 0,
        "plans": plans,
        "remaining": [
            {"apiName": n, "count": c - used[n]}
            for n, c in owned.items()
            if c > used[n]
        ],
        "version": context.get("version"),
        "candidateOptions": options,
    }
