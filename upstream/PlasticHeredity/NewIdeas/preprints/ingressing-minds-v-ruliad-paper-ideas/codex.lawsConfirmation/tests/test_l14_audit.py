import ast
from pathlib import Path

from laws_confirmation.artifact_audit import InputTracker
from laws_confirmation.l14_audit import (
    _dataclass_field_count,
    _imports_from_tree,
    _logical_line_count,
    _registered_gate_count,
    calculate_min_energy_table,
    dependency_closure,
    intervention_energy_audit,
    rows_csv,
    timescale_audit,
)


def test_static_source_metrics_are_explicit() -> None:
    source = """
# comment
from dataclasses import dataclass

@dataclass(frozen=True)
class Config:
    alpha: float = 1.0
    beta: int = 2

from sibling.module import value
import numpy as np
"""
    tree = ast.parse(source)
    assert _logical_line_count(source) == 7
    assert _dataclass_field_count(tree) == 2
    assert _imports_from_tree(tree) == {"dataclasses", "sibling", "numpy"}


def test_gate_count_tolerates_wrapped_heading_and_stops_at_next_section() -> None:
    text = """
## Gates (adjudicated as E33; prophecies frozen in
## WAVE7_PROPHECIES.md)

1. first gate
2. second gate
3. third gate

## Later section

1. not a gate
"""
    assert _registered_gate_count(text) == 3
    assert _registered_gate_count("## No criteria\n") is None


def test_dependency_closure_is_transitive_and_cycle_safe() -> None:
    graph = {
        "root": {"left", "right"},
        "left": {"base"},
        "right": {"base"},
        "base": {"root"},
    }
    assert dependency_closure("root", graph) == ("base", "left", "right", "root")


def test_min_energy_recalculation_uses_success_threshold() -> None:
    details = {
        "A:L1": {
            "low": {"energy": 1.0, "rate": 0.49},
            "high": {"energy": 3.0, "rate": 0.5},
        },
        "A:L2": {"only": {"energy": 0.1, "rate": 0.0}},
    }
    assert calculate_min_energy_table(details) == {"A:L1": 3.0, "A:L2": None}

    payload = {
        "details": details,
        "gates": {
            "min_energy_table": {"A:L1": 3.0, "A:L2": None},
            "gate_p37_2_information_wins_on_D": False,
            "gate_p37_3_reinforcement_cheapens": False,
        },
    }
    audit = intervention_energy_audit(payload)
    assert audit["all_values_match"] is True
    assert audit["working_rung_lever_pairs"] == {"A:L1": 3.0}
    assert audit["is_common_price_for_four_l14_competencies"] is False


def test_timescale_audit_does_not_infer_repair_effect_from_freedom_square() -> None:
    square = {
        "chosen": "0.1|0.2",
        "square": {
            "0.1|0.2": {"freedom_pass": True, "conversion": 0.2},
            "0.2|0.2": {"freedom_pass": True, "conversion": 0.1},
            "0.1|0.4": {"freedom_pass": False, "conversion": 0.0},
            "0.2|0.4": {"freedom_pass": False, "conversion": 0.0},
        },
    }
    triangle = {"gates": {"gate_p49_1_transport": True}}
    audit = timescale_audit(square, triangle)
    assert audit["all_tested_rhos_pass_freedom_at_chosen_gain"] is True
    assert audit["rho_varied_on_repair_endpoint"] is False
    assert audit["time_identified_as_the_causal_price"] is False


def test_csv_serializes_nested_cells_without_losing_rows() -> None:
    value = rows_csv(
        [{"name": "one", "nested": {"b": 2, "a": 1}}],
        ("name", "nested"),
    )
    assert value.splitlines()[0] == "name,nested"
    assert "one" in value
    assert '""a"":1' in value


def test_input_tracker_remains_compatible_with_static_audit(tmp_path: Path) -> None:
    path = tmp_path / "input.txt"
    path.write_text("evidence\n", encoding="utf-8")
    tracker = InputTracker()
    tracker.add(path)
    assert tracker.paths == {path.resolve()}
