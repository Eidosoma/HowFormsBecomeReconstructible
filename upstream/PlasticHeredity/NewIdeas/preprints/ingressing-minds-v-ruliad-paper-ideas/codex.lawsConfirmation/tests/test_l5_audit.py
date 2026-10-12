import json
from pathlib import Path

from laws_confirmation.l5_audit import (
    _battery2_calculations,
    _battery3_calculations,
    _recursive_close,
    source_config_digests,
)
from laws_confirmation.selfhood_math import recalculate_e27, recalculate_e30


IDEAS = Path(__file__).resolve().parents[2]


def _shard_entries(package: str, pattern: str):
    rows = []
    for path in sorted((IDEAS / package / "results/full/work").glob(pattern)):
        rows.extend(json.loads(path.read_text(encoding="utf-8"))["entries"])
    return rows


def test_l5_source_config_digests_match_retained_defaults():
    assert source_config_digests() == {
        "voltage_web_screen_base": "344f79b642e1bff65c2ab40f6a068b485e0f770eee79e3ec55edadda788c633c",
        "voltage_web_current": "160a66a2a401be57a75c4518b1d7dd847aa7e925e35054733a7f18710af76ac0",
        "setpoint_rewrite": "48ac009655861e57fbcf6da4c08c982092f43910ed7828b170436dbf7391eee1",
        "anatomical_homeostasis": "65cda1310be7a0d54130c03bb2007ea13f7b44f4ab0399c94673700a267bddff",
        "sealed_battery_2": "4109c2f23d1dadce602ae199443b6a6f214aad5fb6383aad9b42dfba5091b82b",
        "sealed_battery_3": "8a27efba409f1b8e3ca131112a5f3c1535983d33b78da86e99662703df6724ed",
    }


def test_retained_e27_reconstructs_and_keeps_declared_gate_failure():
    entries = _shard_entries("setpoint_rewrite", "rewrite_shard_*_of_08.json")
    summary = json.loads(
        (IDEAS / "setpoint_rewrite/results/full/rewrite_summary.json").read_text(
            encoding="utf-8"
        )
    )
    result = recalculate_e27(entries)
    assert _recursive_close(result["source_projection"], summary["gates"])
    assert result["row_census"] == {
        "total": 80,
        "band": 48,
        "under": 16,
        "over": 16,
        "unique": 80,
    }
    assert result["declared_expectations_two_setpoint_gate"]["calculated"] is False
    assert result["implemented_two_setpoint_gate"]["calculated"] is False
    assert result["recovery_contrast"]["directions"]["positive"] == 48


def test_retained_e30_reconstructs_and_asymmetry_is_adverse():
    entries = _shard_entries(
        "anatomical_homeostasis", "homeo_shard_*_of_08.json"
    )
    summary = json.loads(
        (IDEAS / "anatomical_homeostasis/results/full/homeo_summary.json").read_text(
            encoding="utf-8"
        )
    )
    result = recalculate_e30(entries)
    assert _recursive_close(result["source_projection"], summary["gates"])
    assert result["source_projection"]["n_types_passing"] == 6
    assert result["source_projection"]["gate_asymmetry"] is False
    assert result["recovery_contrast"]["per_type_directions"] == {
        "positive": 2,
        "ties": 0,
        "negative": 4,
        "n": 6,
    }
    low, high = result["recovery_contrast"]["bootstrap"]["percentile_95"]
    assert low < 0 < high


def test_battery2_all_component_booleans_recalculate():
    root = IDEAS / "sealed_battery_2/results/full"
    names = ("ladder", "redemption", "regime", "worm", "placements")
    components = {
        name: json.loads(
            (root / f"component_{name}.json").read_text(encoding="utf-8")
        )
        for name in names
    }
    result = _battery2_calculations(components)
    assert all(result[name] == components[name]["gate"] for name in names)


def test_battery3_all_component_booleans_recalculate():
    root = IDEAS / "sealed_battery_3/results/full"
    names = ("recovery", "training", "equifinality", "amplifier", "generalization")
    components = {
        name: json.loads(
            (root / f"component_{name}.json").read_text(encoding="utf-8")
        )
        for name in names
    }
    result = _battery3_calculations(components)
    assert all(result[name] == components[name]["gate"] for name in names)
