from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from grn_reset_audit.contingency import (
    CONTINGENCY_CONTROLS,
    LINEAGE_ARMS,
    RELATIONAL_TASKS,
    SCHEDULES,
    TRANSFER_CONTROLS,
    _parallel,
    _project_campaign,
    _state_from_normalized,
    axis_score,
    bipolar_score,
    carrier_decision,
    control_median_envelope,
    exposure_decision,
    load_contingency_config,
    native_transfer_decision,
    residual_audit,
    renewal_decision,
    schedule_exposure_counts,
    schedule_stimuli,
    two_cue_decision,
)
from grn_reset_audit.artifacts import write_json
from grn_reset_audit.engine import PhaseResult, State, run_epoch_schedule
from grn_reset_audit.upstream import PINNED_COMMIT
from grn_reset_audit.verification import CONTINGENCY_RECORD_FILES, verify_run


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs" / "grn-contingency-memory-v1.json"
ATLAS = ROOT / "runs" / "grn-observer-atlas-v1"
FORM = ROOT / "runs" / "grn-ca-bridge-ladder-v1-form-qualification"


def test_protocol_freezes_cohorts_timing_seeds_and_four_hour_cap():
    config = load_contingency_config(CONFIG)
    assert tuple(config["relational_candidate_task_ids"]) == RELATIONAL_TASKS
    assert tuple(config["schedule_templates"]) == SCHEDULES
    assert config["max_workers"] == 4
    assert config["hard_wall_seconds"] == 14400.0
    assert config["hard_aggregate_cpu_seconds"] == 57600.0
    assert tuple(config["washout_checkpoints"]) == (2500.0, 12500.0)
    seed_groups = [
        config["timing_discovery"]["seed_indices"],
        config["contingency_validation"]["seed_indices"],
        config["exposure_validation"]["seed_indices"],
        config["two_cue_reversal"]["seed_indices"],
        config["native_transfer"]["seed_indices"],
        config["carrier_dissection"]["discovery_seed_indices"],
        config["carrier_dissection"]["validation_seed_indices"],
        config["active_renewal"]["seed_indices"],
    ]
    flat = [seed for group in seed_groups for seed in group]
    assert len(flat) == len(set(flat))


def test_protocol_rejects_worker_schedule_and_seed_leakage(tmp_path):
    payload = json.loads(CONFIG.read_text())
    payload["max_workers"] = 5
    changed = tmp_path / "workers.json"
    changed.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="cap workers at four"):
        load_contingency_config(changed)

    payload = json.loads(CONFIG.read_text())
    payload["schedule_templates"]["blocked"][0] = "-"
    changed = tmp_path / "schedule.json"
    changed.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="five CS and UCS"):
        load_contingency_config(changed)

    payload = json.loads(CONFIG.read_text())
    payload["native_transfer"]["seed_indices"][0] = payload["two_cue_reversal"]["seed_indices"][0]
    changed = tmp_path / "leakage.json"
    changed.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="seeds overlap"):
        load_contingency_config(changed)


def test_all_timing_schedules_are_dose_matched_and_order_preserving():
    config = load_contingency_config(CONFIG)
    cs = {1: 2.0}
    ucs = {3: -1.0}
    for name, tokens in config["schedule_templates"].items():
        counts = schedule_exposure_counts(tokens)
        assert counts["cs"] == counts["ucs"] == 5
        epochs = schedule_stimuli(tokens, cs, ucs)
        assert len(epochs) == 10
        assert sum(epoch is not None and 1 in epoch for epoch in epochs) == 5
        assert sum(epoch is not None and 3 in epoch for epoch in epochs) == 5
        if name == "blocked":
            assert all(epoch is not None and 1 in epoch for epoch in epochs[:5])
            assert all(epoch is not None and 3 in epoch for epoch in epochs[5:])


def test_coordinates_have_exact_polarity_and_control_envelope_is_strict():
    form_a = np.asarray([2.0, 1.0, -1.0])
    form_b = np.asarray([-2.0, -1.0, 1.0])
    midpoint = 0.5 * (form_a + form_b)
    assert bipolar_score(form_a, form_a, form_b) == pytest.approx(1.0)
    assert bipolar_score(form_b, form_a, form_b) == pytest.approx(-1.0)
    assert bipolar_score(midpoint, form_a, form_b) == pytest.approx(0.0)
    assert axis_score(form_a, midpoint, form_a - midpoint) == pytest.approx(1.0)
    assert bipolar_score(form_a, form_a, form_a) is None
    envelope, medians = control_median_envelope(
        {"clean": [0.0] * 16, "failed": [0.6] * 16}
    )
    assert medians == {"clean": 0.0, "failed": 0.6}
    assert envelope == pytest.approx(0.6)


class ScheduleBackend:
    delta_t = 1.0

    def __init__(self):
        self.calls = []

    @staticmethod
    def _sample_columns(values, count):
        indices = np.rint(np.linspace(0, values.shape[1] - 1, count)).astype(int)
        return values[:, indices]

    def run_phase(
        self,
        state,
        duration,
        stimuli,
        response_id,
        sample_count=101,
        pulse_count=1,
    ):
        self.calls.append((duration, stimuli, pulse_count))
        increment = 0.0 if stimuli is None else sum(stimuli.values())
        y = state.y + increment
        samples = np.repeat(y[:, None], 3, axis=1)
        return PhaseResult(
            State(y, state.w.copy(), state.c.copy(), state.t + duration),
            y,
            y,
            samples,
            samples[response_id],
            True,
            0.25,
            0.20,
        )


def test_epoch_schedule_chains_state_and_preserves_rulebook():
    backend = ScheduleBackend()
    initial = State(np.asarray([0.0, 1.0]), np.asarray([2.0]), np.asarray([9.0]), 4.0)
    result = run_epoch_schedule(
        backend,
        initial,
        [{0: 1.0}, None, {0: 2.0}],
        10.0,
        response_id=0,
        sample_count=5,
    )
    assert [call[1] for call in backend.calls] == [{0: 1.0}, None, {0: 2.0}]
    assert all(call[2] == 1 for call in backend.calls)
    assert result.state.t == pytest.approx(34.0)
    assert result.state.y[0] == pytest.approx(3.0)
    assert np.array_equal(result.state.c, initial.c)
    assert result.sampled_y.shape == (2, 5)
    assert result.cpu_seconds == pytest.approx(0.75)


def _history_row(task_id, seed, condition, score, fingerprint):
    return {
        "task_id": f"history|{task_id}|{seed}|{condition}",
        "memory_task_id": task_id,
        "seed_index": seed,
        "condition": condition,
        "valid": True,
        "scores": {"2500": score, "12500": score},
        "checkpoints": {
            "2500": {"fingerprint": fingerprint},
            "12500": {"fingerprint": fingerprint},
        },
    }


def test_synthetic_exposure_and_counterbalanced_two_cue_tracks_pass():
    config = load_contingency_config(CONFIG)
    exposure_rows = []
    for task_id in config["exposure_anchor_task_ids"]:
        for seed in config["exposure_validation"]["seed_indices"]:
            exposure_rows.append(_history_row(task_id, seed, "low_ucs", -1.0, [-1.0, -1.0, -1.0]))
            exposure_rows.append(_history_row(task_id, seed, "high_ucs", 1.0, [1.0, 1.0, 1.0]))
    exposure = exposure_decision(exposure_rows, config)
    assert exposure["pass"]
    assert len(exposure["transfer_candidates"]) == 2

    task_id = config["relational_candidate_task_ids"][0]
    candidate = {
        "memory_task_id": task_id,
        "model_id": int(task_id.split("-")[0]),
        "selected_schedule": "coincident",
        "channel_class": "relational",
    }
    fingerprints = {
        "form_a": [0.0, 1.0, -1.0, 0.0],
        "form_b": [0.0, -1.0, 1.0, 0.0],
        "mixed": [0.0, 0.0, 0.0, 0.0],
    }
    two_cue_rows = []
    for seed in config["two_cue_reversal"]["seed_indices"]:
        for condition, fingerprint in fingerprints.items():
            row = _history_row(task_id, seed, condition, 0.0, fingerprint)
            row["cue2"] = {"node_id": 3, "value": 1.0}
            row["schedule_exposures"] = {"cue1": 5, "cue2": 5, "ucs": 5}
            two_cue_rows.append(row)
    assert all(
        row["schedule_exposures"] == {"cue1": 5, "cue2": 5, "ucs": 5}
        for row in two_cue_rows
    )
    two_cue = two_cue_decision(two_cue_rows, [candidate], config)
    assert two_cue["pass"]
    assert two_cue["transfer_candidates"][0]["memory_task_id"] == task_id


def _transfer_records(config, task_id):
    records = []
    for environment in ("exact", "moderate"):
        for seed in config["native_transfer"]["seed_indices"]:
            for history, sign in (("a", 1.0), ("b", -1.0)):
                for condition in TRANSFER_CONTROLS:
                    score = sign if condition == "intact" else -sign if condition in {"opposite", "inversion"} else 0.0
                    records.append(
                        {
                            "task_id": f"transfer|{task_id}|{environment}|{seed}|{history}|{condition}",
                            "memory_task_id": task_id,
                            "seed_index": seed,
                            "state_mode": "y",
                            "environment": environment,
                            "history": history,
                            "condition": condition,
                            "score": score,
                            "valid": True,
                        }
                    )
    return records


def test_native_transfer_requires_content_reversal_and_every_control_family():
    config = load_contingency_config(CONFIG)
    task_id = config["relational_candidate_task_ids"][0]
    candidate = {"memory_task_id": task_id, "model_id": 10, "channel_class": "relational"}
    records = _transfer_records(config, task_id)
    decision = native_transfer_decision(records, [candidate], config)
    assert decision["pass"]
    assert decision["carrier_candidates"][0]["state_mode"] == "y"

    for row in records:
        if row["condition"] == "normalized_shuffle":
            row["score"] = 0.6
    failed = native_transfer_decision(records, [candidate], config)
    assert not failed["pass"]
    assert failed["channel_summaries"][0]["environments"]["exact"]["control_median_abs"] == pytest.approx(0.6)


def _causal_score(history, condition):
    sign = 1.0 if history == "a" else -1.0
    if condition in {"intact", "rescue", "rescue_g3", "active"}:
        return sign if condition not in {"rescue", "rescue_g3"} else 0.8 * sign
    if condition in {"wrong_content", "inversion"}:
        return -sign
    return 0.0


def test_carrier_and_g8_renewal_require_ablation_rescue_and_inversion():
    config = load_contingency_config(CONFIG)
    task_id = config["relational_candidate_task_ids"][0]
    candidate = {"memory_task_id": task_id, "model_id": 10, "channel_class": "relational", "state_mode": "y"}
    validation = []
    carrier_conditions = (
        "intact", "matched_background", "erase", "inversion", "wrong_content",
        "normalized_shuffle", "norm_matched_random", "rescue",
    )
    for seed in config["carrier_dissection"]["validation_seed_indices"]:
        for history in ("a", "b"):
            for condition in carrier_conditions:
                validation.append(
                    {
                        "task_id": f"carrier|{seed}|{history}|{condition}",
                        "memory_task_id": task_id,
                        "seed_index": seed,
                        "history": history,
                        "condition": condition,
                        "score": _causal_score(history, condition),
                        "valid": True,
                    }
                )
    shard = {
        "candidate": candidate,
        "selected_codec": {"codec_id": "direction-r1", "payload_float_count": 1},
        "fixed_state_scale": [1.0, 1.0],
        "validation_records": validation,
    }
    carrier = carrier_decision([shard], config)
    assert carrier["pass"]

    renewal_candidate = carrier["renewal_candidates"][0]
    renewal_rows = []
    for generation in (4, 8):
        for seed in config["active_renewal"]["seed_indices"]:
            for history in ("a", "b"):
                for condition in LINEAGE_ARMS:
                    renewal_rows.append(
                        {
                            "task_id": f"renewal|{generation}|{seed}|{history}|{condition}",
                            "memory_task_id": task_id,
                            "seed_index": seed,
                            "generation": generation,
                            "history": history,
                            "condition": condition,
                            "score": _causal_score(history, condition),
                            "valid": True,
                        }
                    )
    renewal = renewal_decision(renewal_rows, [renewal_candidate], config)
    assert renewal["pass"]
    assert renewal["channel_summaries"][0]["classification"] == "relational-plastic-heredity"

    for row in validation:
        if row["condition"] == "inversion":
            row["score"] *= -1.0
    assert not carrier_decision([{**shard, "validation_records": validation}], config)["pass"]


def test_state_transfer_changes_only_declared_dynamic_coordinates():
    baseline = State(
        np.asarray([0.1, 0.2]),
        np.asarray([0.3]),
        np.asarray([7.0, 8.0]),
        12.0,
    )
    memory = SimpleNamespace(bounds=np.asarray([[-1.0, 1.0], [-2.0, 2.0]]))
    child_y = _state_from_normalized([0.5, -0.5], baseline, np.ones(2), memory, "y")
    assert np.array_equal(child_y.c, baseline.c)
    assert np.array_equal(child_y.w, baseline.w)
    child_yw = _state_from_normalized([0.5, -0.5, 1.0], baseline, np.ones(3), memory, "yw")
    assert np.array_equal(child_yw.c, baseline.c)
    assert child_yw.w[0] == pytest.approx(1.3)


def test_one_and_four_worker_order_is_identical():
    args = [(1, "a"), (2, "b"), (3, "c"), (4, "d")]
    assert _parallel(tuple, args, 1) == _parallel(tuple, args, 4)


def test_verifier_accepts_sealed_schema_and_rejects_silent_founder_reuse(tmp_path):
    config = load_contingency_config(CONFIG)
    write_json(
        tmp_path / "registration.json",
        {
            "protocol": config,
            "upstream": {"commit": PINNED_COMMIT},
            "workers": 4,
            "record_files": CONTINGENCY_RECORD_FILES,
        },
    )
    write_json(tmp_path / "state.json", {"status": "completed"})
    write_json(
        tmp_path / "resource-ledger.json",
        {"aggregate_cpu_seconds": 1.0, "active_wall_seconds": 1.0},
    )
    write_json(tmp_path / "parent-gate.json", {"pass": True})
    write_json(
        tmp_path / "analysis.json",
        {"minimum_completion_gate": True, "run_status": "completed"},
    )
    write_json(tmp_path / "decision.json", {"pass": False})
    write_json(tmp_path / "runtime-incidents.json", {"incidents": []})
    write_json(
        tmp_path / "codebooks.json",
        {
            "discovery_seed_indices": [500],
            "validation_seed_indices": [600],
            "leakage_allowed": False,
        },
    )
    for name in CONTINGENCY_RECORD_FILES:
        (tmp_path / name).write_text("")
    assert verify_run(tmp_path, require_sealed=False)["experiment_kind"] == "contingency-memory-campaign"

    (tmp_path / "active-renewal.jsonl").write_text(
        json.dumps(
            {
                "task_id": "bad-passive-g4",
                "condition": "passive",
                "generation": 4,
                "founder_reused": False,
                "donor_source": "founder",
            }
        )
        + "\n"
    )
    with pytest.raises(ValueError, match="passive contingency lineage reused"):
        verify_run(tmp_path, require_sealed=False)


@pytest.mark.skipif(not (ATLAS / "calibration.jsonl").is_file() or not (FORM / "screen.jsonl").is_file(), reason="sealed parents are not in the test context")
def test_frozen_parent_residuals_and_empirical_projection_are_reproducible():
    config = load_contingency_config(CONFIG)
    audit = residual_audit(config, ATLAS, FORM)
    rows = {row["memory_task_id"]: row for row in audit["references"]}
    assert rows["10-1-25"]["long_relational_rms"] == pytest.approx(5.239769164316602)
    assert rows["29-0-2"]["long_relational_rms"] == pytest.approx(3.0915038427747388)
    projection = _project_campaign(config, ATLAS, FORM)
    assert projection["worst_case_aggregate_cpu_seconds"] < config["soft_aggregate_cpu_seconds"]
    assert projection["worst_case_active_wall_seconds_at_four_workers"] < config["soft_wall_seconds"]
    assert set(projection["stage_projected_cpu_seconds"]) == {
        "timing-discovery", "contingency-validation", "exposure-validation",
        "cue-calibration", "two-cue-reversal", "native-transfer",
        "carrier-dissection", "active-renewal",
    }
    assert projection["safety_factor"] == pytest.approx(1.7)
