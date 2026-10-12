from __future__ import annotations

from pathlib import Path

from gre_sim.local_ph_dynamics import LocalCarrierState
from gre_sim.wagner_ph_ladder_analysis import analyze_ladder_results
from gre_sim.wagner_ph_ladder_campaign import wagner_ph_ladder_status
from gre_sim.wagner_ph_ladder_experiment import (
    quantization_levels,
    quantize_carrier,
    sample_ladder_task,
)
from gre_sim.wagner_ph_ladder_protocols import wagner_ph_ladder_spec


def test_ladder_contract_is_four_hour_cpu_only_and_reserves_confirmation() -> None:
    spec = wagner_ph_ladder_spec()
    assert spec.tasks == 12
    assert spec.capacity_cell_count == 15
    assert spec.coordination_cell_count == 75
    assert spec.ecology_cell_count == 30
    assert spec.maximum_workers == 4
    assert spec.hard_wall_seconds == 14_400
    assert spec.soft_wall_seconds == 13_500
    assert spec.master_seed != spec.confirmation_seed
    assert spec.confirmation_tasks == 24
    smoke = wagner_ph_ladder_spec(smoke=True)
    assert smoke.master_seed != spec.master_seed
    assert smoke.confirmation_seed != spec.confirmation_seed


def test_quantizer_has_exact_zero_bounded_alphabet_and_inactive_zeroes() -> None:
    for bits in (2, 4, 8):
        levels = quantization_levels(bits)
        assert len(levels) == 2**bits - 1
        assert 0.0 in levels
        assert levels[0] == -1.0 and levels[-1] == 1.0
    raw = LocalCarrierState((-0.8, -0.1, 0.2, 0.9) + (1.0,) * 6)
    quantized = quantize_carrier(raw, (0, 2), 2)
    assert quantized.values == (-1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)


def test_task_sampling_is_replayable_and_outcome_blind() -> None:
    spec = wagner_ph_ladder_spec(smoke=True)
    left = sample_ladder_task(spec, 0)
    right = sample_ladder_task(spec, 0)
    assert left == right
    assert left["selection_is_outcome_blind"] is True
    assert left["task_digest"]
    assert set(left["forced_breaks"]) == {"A", "B"}


def _lineage_conditions(
    intact: float,
    zero: float,
    renewal: float,
    reader: float,
    founder: float,
    opposite_correct: float,
    opposite_wrong: float,
) -> dict:
    def values(rate: float, wrong: float = 0.0) -> dict:
        return {
            "0": {
                "correct_rate": rate,
                "wrong_rate": wrong,
                "return_rate": rate,
                "carrier_norm": rate,
                "nonzero_marks": rate,
                "observations": 8,
            },
            "8": {
                "correct_rate": rate,
                "wrong_rate": wrong,
                "return_rate": rate,
                "carrier_norm": rate,
                "nonzero_marks": rate,
                "observations": 8,
            },
        }

    return {
        "intact": values(intact),
        "zero": values(zero),
        "renewal_off": values(renewal),
        "reader_off": values(reader),
        "founder_write_off": values(founder),
        "opposite_history_transplant": values(opposite_correct, opposite_wrong),
    }


def _fake_result() -> tuple[dict, object]:
    spec = wagner_ph_ladder_spec(smoke=True)
    capacity = []
    for k in spec.capacities:
        for bits in spec.bits_per_mark:
            passing = k == 10 and bits == 4
            capacity.append(
                {
                    "cell_id": f"k{k}.b{bits}",
                    "k": k,
                    "bits_per_mark": bits,
                    "alphabet_size": 2**bits - 1,
                    "payload_upper_bits": k * bits,
                    "conditions": _lineage_conditions(
                        0.85 if passing else 0.20,
                        0.10,
                        0.20 if passing else 0.20,
                        0.10 if passing else 0.20,
                        0.10,
                        0.05,
                        0.80 if passing else 0.05,
                    ),
                }
            )
    coordination = []
    for k in spec.coordination_capacities:
        for wi, writer in enumerate(spec.writer_rates):
            for ri, reader in enumerate(spec.reader_couplings):
                strong = k == 10 and wi == len(spec.writer_rates) - 1 and ri == len(spec.reader_couplings) - 1
                rate = 0.85 if strong else 0.10
                renewal = 0.20 if strong else rate
                coordination.append(
                    {
                        "cell_id": f"k{k}.w{wi}.r{ri}",
                        "k": k,
                        "writer_index": wi,
                        "reader_index": ri,
                        "write_rate": writer,
                        "coupling": reader,
                        "conditions": {
                            "intact": _lineage_conditions(rate, rate, rate, rate, rate, 0, 0)["intact"],
                            "renewal_off": _lineage_conditions(renewal, renewal, renewal, renewal, renewal, 0, 0)["intact"],
                        },
                    }
                )
    ecology = []
    for k in spec.ecology_capacities:
        for rho in spec.ecology_persistence:
            useful = k == 10 and rho == 1.0

            def ecological(rate: float) -> dict:
                return {
                    "overall": {"correct_rate": rate, "wrong_rate": 0.0, "return_rate": rate, "observations": 8},
                    "stay": {"correct_rate": rate if rho == 1.0 else None, "wrong_rate": 0.0 if rho == 1.0 else None, "return_rate": rate if rho == 1.0 else None, "observations": 8 if rho == 1.0 else 0},
                    "switch": {"correct_rate": rate if rho == 0.0 else None, "wrong_rate": 0.0 if rho == 0.0 else None, "return_rate": rate if rho == 0.0 else None, "observations": 8 if rho == 0.0 else 0},
                }

            ecology.append(
                {
                    "cell_id": f"k{k}.rho{rho:.2f}",
                    "k": k,
                    "persistence": rho,
                    "conditions": {
                        "intact": ecological(0.80 if useful else (0.05 if rho == 0.0 else 0.20)),
                        "zero": ecological(0.20),
                        "reader_off": ecological(0.20),
                        "renewal_off": ecological(0.20),
                    },
                }
            )
    return {
        "task_id": "task-000",
        "acquisition_rate": 1.0,
        "capacity": capacity,
        "coordination": coordination,
        "ecology": ecology,
    }, spec


def test_analysis_separates_capacity_coordination_and_ecological_barriers() -> None:
    result, spec = _fake_result()
    autopsy = {
        "diagnosis": {
            "training_generalization_gap_present": True,
            "capacity_collapsed_to_k1": True,
        }
    }
    analysis = analyze_ladder_results([result], spec, autopsy)
    assert analysis["capacity_frontier"]["capacity_barrier_supported"] is True
    assert analysis["coordination_surface"]["coordination_valley_supported_any_capacity"] is True
    assert analysis["ecological_value_map"]["any_ecological_usefulness"] is True
    assert analysis["finalist"]["capacity_cell"] == "k10.b4"
    assert analysis["confirmation_reserve"]["status"] == "untouched"
    assert analysis["confirmation_reserve"]["rng_draws_consumed"] == 0


def test_status_is_read_only_for_missing_run(tmp_path: Path) -> None:
    target = tmp_path / "missing"
    assert wagner_ph_ladder_status(target)["status"] == "not-started"
    assert not target.exists()


def test_detached_ladder_has_persistent_four_hour_guard() -> None:
    runner = Path("scripts/run-wagner-ph-ladder-detached.sh").read_text()
    status = Path("scripts/status-wagner-ph-ladder.sh").read_text()
    assert "maximum_wall_seconds=14400" in runner
    assert "soft_wall_seconds=13500" in runner
    assert "maximum_start_load=18" in runner
    assert "waiting-for-load" in runner
    assert "pending-load-admission" in runner
    assert "GRE_WAGNER_PH_LADDER_SOFT_DEADLINE_EPOCH" in runner
    assert "GRE_WAGNER_PH_LADDER_PRIOR_CONSUMED_SECONDS" in runner
    assert "time-budget-exhausted" in runner
    assert "sleep 30" in runner and "kill -KILL" in runner
    assert "heartbeat age" in status
