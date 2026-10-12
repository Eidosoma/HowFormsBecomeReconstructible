from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from gre_sim.config import StudySpec
from gre_sim.mechanism_config import MechanismCondition, MechanismSpec, SourceSetSpec
from gre_sim.mechanism_protocols import phase_3_spec
from gre_sim.mechanism_selection import (
    _endpoint_engineering_audit,
    _phase_3_condition_pairs,
    audit_compiled_bridge,
    phase_2_decision,
)
from gre_sim.mechanism_study import run_mechanism_study
from gre_sim.study import run_study


def _engineering_fixture() -> tuple[dict, list]:
    spec = phase_3_spec()
    pairs = _phase_3_condition_pairs(spec)
    rates: dict[str, dict[str, float]] = {}
    reliability: dict[str, float] = {}
    committor: dict[str, dict] = {}
    endpoints = (
        "frozen_library",
        "exact_point_state",
        "realized_signature",
        "competing_outcome",
    )
    fields = (
        "active_capture",
        "stable_point_capture",
        "stable_signature_capture",
        "strict_library",
        "strict_state",
    )
    for main, controls, genes in pairs:
        for variance in main.gamma_variances:
            for mode in main.inheritance_modes:
                acute_base = (
                    f"{main.name}.{main.variant}.N-{genes}.acute_mismatch."
                    f"lambda-1.theta-{variance:g}.{mode}"
                )
                for field in fields:
                    rates[f"{acute_base}.{field}"] = {"mean": 0.90}
                for endpoint in endpoints:
                    reliability[f"{endpoint}.{acute_base}"] = 0.90
                    committor[f"{endpoint}.{acute_base}"] = {
                        "mean_log_loss_gain": 0.0,
                        "mean_brier_gain": 0.0,
                        "committor_log_loss": 1.0,
                        "baseline_log_loss": 1.0,
                        "interval": [0.0, 0.0],
                    }
        for carryover in set(main.carryover_values) & set(controls.carryover_values):
            for variance in set(main.gamma_variances) & set(controls.gamma_variances):
                for mode in set(main.inheritance_modes) & set(controls.inheritance_modes):
                    for condition, arm in (
                        (main, "natural"),
                        (controls, "joint_isomorphic"),
                        (controls, "single_attractor"),
                    ):
                        base = (
                            f"{condition.name}.{condition.variant}.N-{genes}.{arm}."
                            f"lambda-{carryover:g}.theta-{variance:g}.{mode}"
                        )
                        for field in fields:
                            rates[f"{base}.{field}"] = {"mean": 0.90}
    return {
        "rates": rates,
        "split_half_reliability": reliability,
        "committor": committor,
    }, pairs


def test_endpoint_engineering_gate_is_sign_independent_and_complete() -> None:
    analysis, pairs = _engineering_fixture()
    assert len(pairs) == 2
    fields = {
        "frozen_library": "active_capture",
        "exact_point_state": "stable_point_capture",
        "realized_signature": "stable_signature_capture",
        "competing_outcome": None,
    }
    for endpoint, field in fields.items():
        audit = _endpoint_engineering_audit(analysis, pairs, endpoint, field)
        assert all(audit["criteria"].values())

    main, controls, genes = pairs[0]
    key = (
        f"{controls.name}.{controls.variant}.N-{genes}.joint_isomorphic."
        "lambda-0.theta-0.self.active_capture"
    )
    analysis["rates"][key]["mean"] = 0.86
    audit = _endpoint_engineering_audit(
        analysis, pairs, "frozen_library", "active_capture"
    )
    assert not audit["criteria"]["joint_isomorphic_margin_at_most_0_03"]


def test_compiled_bridge_is_order_independent_and_forces_phase_2(tmp_path: Path) -> None:
    parent_spec = replace(
        StudySpec.quick_v2(), cohorts=("sampled",), launch_states_per_rulebook=2
    )
    parent = tmp_path / "parent"
    run_study(parent_spec, parent, workers=1)

    source = SourceSetSpec(
        "stage_a_wagner", "wagner", 10, 1, "parent", "wagner"
    )
    common = {
        "source_set": source.name,
        "arms": ("natural", "acute_mismatch"),
        "carryover_values": (0.0, 1.0),
        "inheritance_modes": ("self", "donor_shuffled"),
        "gamma_variances": (0.0,),
        "futures_per_cell": 4,
    }
    spec = MechanismSpec(
        cohort_id="compiled-bridge-fixture",
        phase="test",
        master_seed="5e7c9dd8381f516f5dd32eac60e0887f",
        source_sets=(source,),
        conditions=(
            MechanismCondition("wagner-main", variant="wagner_sequential", **common),
            MechanismCondition(
                "wagner-compiled-main", variant="wagner_compiled", **common
            ),
        ),
        launch_states_per_rulebook=2,
        horizon=12,
        stable_destination_run=2,
        strict_run=2,
        bootstrap_repetitions=16,
    )
    destination = tmp_path / "mechanism"
    run_mechanism_study(spec, destination, parent, workers=1)
    bridge = audit_compiled_bridge(destination)
    assert bridge["pathwise_equal"]
    assert bridge["native_futures"] == bridge["compiled_futures"]
    assert phase_2_decision(destination)["phase_2_required"]
