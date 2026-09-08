import pytest

from tft_spot.data.augment_identity import build_augment_aliases
from tft_spot.engine.compiler import compile_workspace


def test_identity_uses_name_tier_and_set_in_source_order():
    catalog = {
        "first": {"set": 18, "tier": 2, "name": "Consuming Flora"},
        "second": {"set": 18, "tier": 2, "name": "Consuming Flora"},
        "silver": {"set": 18, "tier": 1, "name": "Consuming Flora"},
        "next-set": {"set": 19, "tier": 2, "name": "Consuming Flora"},
        "different-name": {"set": 18, "tier": 2, "name": "Other Flora"},
    }
    assert build_augment_aliases(catalog) == {
        "first": "first",
        "second": "first",
        "silver": "silver",
        "next-set": "next-set",
        "different-name": "different-name",
    }


def test_compiler_collapses_equal_priorities_but_rejects_conflicts():
    config = {
        "sourceId": "comp",
        "setNumber": 18,
        "status": "ready",
        "units": [],
        "components": [],
        "augments": [
            {"apiName": "first", "priority": "high"},
            {"apiName": "second", "priority": "high"},
        ],
    }
    workspace = {
        "source": {"sourceId": "comp", "set": 18, "title": "Example"},
        "configuration": config,
        "earlyUnits": [],
        "components": [],
        "augments": [{"apiName": "first"}, {"apiName": "second"}],
    }
    aliases = {"first": "first", "second": "first"}
    compiled = compile_workspace(workspace, aliases)
    assert len(compiled.augments) == 1
    assert compiled.augments[0].priority == "high"
    config["augments"][1]["priority"] = "avoid"
    with pytest.raises(ValueError, match="Conflicting priorities"):
        compile_workspace(workspace, aliases)
