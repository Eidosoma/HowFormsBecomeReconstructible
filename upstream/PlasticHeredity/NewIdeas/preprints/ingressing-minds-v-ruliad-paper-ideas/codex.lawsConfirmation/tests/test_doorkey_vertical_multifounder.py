import json
import numpy as np
import pytest

pytest.importorskip("torch")

from laws_confirmation.doorkey_carrier import (
    empty_germ,
    read_germ,
    write_germ_from_local_evidence,
)
from laws_confirmation.doorkey_vertical_multifounder import (
    ARMS,
    CONFIRMATORY_FOUNDERS,
    FOUNDERS,
    GENERATIONS,
    PRIMARY_MARGIN,
    REGISTERED_CELLS,
    ENGINE_RUN,
    RUN_ID,
    _correct_functional_packet,
    _worker_train_cell,
    classify_outcomes,
    exact_alias_audit,
    generation_specs,
    initial_carriers,
    lineage_schedule_audit,
    seed_row,
)
import laws_confirmation.doorkey_vertical_multifounder as multifounder_module


def _correct_carrier() -> np.ndarray:
    evidence = np.zeros((1, 4, 8), dtype=np.float32)
    evidence[0, 1, 4] = 10.0
    evidence[0, 3, 5] = 10.0
    confirmation = np.asarray([[False, True, False, True]])
    carrier, committed = write_germ_from_local_evidence(
        evidence,
        empty_germ(1),
        confirmation_mask=confirmation,
    )
    assert np.array_equal(committed, confirmation)
    return carrier


def _auc(value: float) -> dict:
    return {
        "fixed_random": {
            "events": {
                "open_door": {"reached_fraction_auc": value},
            }
        }
    }


def _synthetic_results(delta: float = 0.10) -> list[dict]:
    carrier = _correct_carrier().tolist()
    results = []
    for founder in FOUNDERS:
        for generation in GENERATIONS:
            values = {
                "rewrite": 0.10 + delta,
                "stale_copy": 0.10 + delta,
                "silence": 0.10,
                "wrong_frozen": 0.10,
                "wrong_rewrite": 0.10 if generation == 1 else 0.10 + delta,
                "reader_off_rewrite": 0.10,
                "lesion_rewrite": 0.10 if generation == 1 else 0.10 + delta,
            }
            for arm in ARMS:
                results.append(
                    {
                        "founder": founder,
                        "generation": generation,
                        "arm": arm,
                        "learning_auc": _auc(values[arm]),
                        "scheduled_next_carrier": carrier,
                        "scheduled_next_carrier_sha256": f"{founder}-{generation}-{arm}",
                        "scheduled_next_source": "writer_candidate",
                        "writer": {
                            "enabled": True,
                            "candidate_carrier_sha256": f"{founder}-{generation}-{arm}",
                            "renewal": {
                                "write_mask": [[False, True, False, True]],
                            },
                        },
                        "incoming_carrier_sha256": (
                            f"source-{founder}-{arm}"
                            if generation == 1
                            else f"{founder}-{generation - 1}-{arm}"
                        ),
                        "behavior_fingerprint": "same",
                    }
                )
    return results


def test_seed_table_is_exact_disjoint_and_complete():
    assert seed_row(0, 1) == {
        "birth": 140_001_000,
        "training": 150_001_000,
        "writer_layout": 160_001_000,
        "writer_action": 170_001_000,
    }
    assert seed_row(3, 3) == {
        "birth": 140_303_000,
        "training": 150_303_000,
        "writer_layout": 160_303_000,
        "writer_action": 170_303_000,
    }
    rows = [
        seed_row(founder, generation)
        for founder in FOUNDERS
        for generation in GENERATIONS
    ]
    values = [value for row in rows for value in row.values()]
    assert len(values) == len(set(values)) == 48
    assert REGISTERED_CELLS == 84
    with pytest.raises(ValueError):
        seed_row(4, 1)


def test_carriers_and_specs_preserve_registered_control_semantics(tmp_path):
    founder = _correct_carrier()
    carriers = initial_carriers(founder)
    checkpoints = {arm: tmp_path / f"{arm}.pt" for arm in ARMS}
    specs = generation_specs(
        2,
        3,
        carriers,
        checkpoints,
        founder=founder,
        wrong=carriers["wrong_frozen"],
        empty=carriers["silence"],
    )
    assert [row["arm"] for row in specs] == list(ARMS)
    assert {row["birth_seed"] for row in specs} == {140_203_000}
    assert {row["training_seed"] for row in specs} == {150_203_000}
    by_arm = {row["arm"]: row for row in specs}
    assert by_arm["reader_off_rewrite"]["germ_mode"] == "blind"
    assert by_arm["stale_copy"]["writer_enabled"]
    assert by_arm["stale_copy"]["schedule_mode"] == "fixed"
    assert not by_arm["silence"]["writer_enabled"]
    assert not by_arm["wrong_frozen"]["writer_enabled"]
    assert by_arm["wrong_rewrite"]["writer_enabled"]
    assert not read_germ(carriers["silence"]).active.any()
    assert not read_germ(carriers["lesion_rewrite"]).active[0, 1]
    assert not read_germ(carriers["lesion_rewrite"]).active[0, 3]


def test_correct_packet_requires_only_fixed_functional_records():
    correct = _correct_carrier()
    assert _correct_functional_packet(correct)["passes"]
    wrong = correct.copy()
    wrong[0, 0] ^= np.uint8(1)
    assert not _correct_functional_packet(wrong)["passes"]
    assert not _correct_functional_packet(np.zeros((2, 64), dtype=np.uint8))["passes"]


def test_alias_and_lineage_audits_cover_every_founder():
    results = _synthetic_results()
    aliases = exact_alias_audit(results)
    schedule = lineage_schedule_audit(results)
    assert aliases["passes"]
    assert len(aliases["comparisons"]) == 24
    assert schedule["passes"]
    assert len(schedule["rows"]) == 56
    results[0]["behavior_fingerprint"] = "different"
    assert not exact_alias_audit(results)["passes"]


def test_registered_endpoint_classification_is_strict_and_anchor_excluded():
    results = _synthetic_results(delta=0.10)
    outcome = classify_outcomes(results)
    assert outcome["confirmation_founders"] == list(CONFIRMATORY_FOUNDERS)
    assert outcome["primary_classification"] == "PRIMARY_REPLICATED_3_OF_3"
    assert outcome["wrong_repair_classification"] == "WRONG_CONTENT_REPAIRED_3_OF_3"
    assert outcome["lesion_rescue_classification"] == "LESION_RESCUED_3_OF_3"
    assert (
        outcome["rewrite_content_classification"]
        == "REWRITE_CONTENT_CORRECT_ALL_12_WRITES"
    )

    # Founder 0 is an anchor and cannot rescue a failed confirmation founder.
    for row in results:
        if row["founder"] == 1 and row["arm"] == "rewrite":
            row["learning_auc"] = _auc(0.10 + PRIMARY_MARGIN - 0.001)
    failed = classify_outcomes(results)
    assert failed["primary_classification"] == "PRIMARY_NOT_REPLICATED_3_OF_3"


def test_worker_adapter_registers_engine_result_and_progress(tmp_path, monkeypatch):
    founder_output = tmp_path / "founder_2"
    progress_dir = founder_output / "progress"
    progress_dir.mkdir(parents=True)
    (progress_dir / "g1_rewrite.json").write_text(
        json.dumps({"status": "COMPLETE"}), encoding="utf-8"
    )

    def fake_worker(spec, config, output_root, output_dir):
        assert output_root == str(tmp_path)
        assert output_dir == str(founder_output)
        return {
            "run_id": ENGINE_RUN,
            "generation": spec["generation"],
            "arm": spec["arm"],
        }

    monkeypatch.setattr(
        multifounder_module.frozen_vertical,
        "_worker_train_cell",
        fake_worker,
    )
    result = _worker_train_cell(
        {
            "founder": 2,
            "founder_role": "confirmation",
            "generation": 1,
            "arm": "rewrite",
        },
        {},
        str(tmp_path),
        str(founder_output),
    )
    assert result["run_id"] == RUN_ID
    assert result["engine_run_id"] == ENGINE_RUN
    assert result["founder"] == 2
    stored = json.loads((founder_output / "g1_rewrite.json").read_text())
    progress = json.loads((progress_dir / "g1_rewrite.json").read_text())
    assert stored == result
    assert progress["run_id"] == RUN_ID
    assert progress["engine_run_id"] == ENGINE_RUN
    assert progress["founder"] == 2
