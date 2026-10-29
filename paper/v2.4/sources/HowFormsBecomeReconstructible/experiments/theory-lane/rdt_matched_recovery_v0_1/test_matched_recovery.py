"""Recovery-stratum confounding, paired intervention contrast and runtime checks."""
from copy import deepcopy
import math
import pytest

import it_common as common
from it_common import ROOT, C, read, ledger
import cp_models
import cp_analysis
import ec_models
import it_run
from test_cheap_probe import unequal_fixture


def test_reproduce_every_saved_prediction_without_fitting(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("This study must not fit models")
    monkeypatch.setattr(ec_models, "fit", forbidden)
    monkeypatch.setattr(ec_models, "objective", forbidden)
    old = read(ROOT / "context/REPLAY_FEATURES.json")["forecasts"]
    saved = read(ROOT / "context/CALIBRATION_FORECAST_SEAL.json")["forecasts"]
    current = cp_models.forecasts(old)
    key = lambda r: (tuple(r["key"]), r["injury"], r["regime"])
    expected = {key(r): r for r in saved}
    assert len(current) == len(expected) == 128
    assert set(expected) == {key(r) for r in current}
    for original, actual in zip(old, current, strict=True):
        ref = expected[key(actual)]
        for name, value in actual["probabilities"].items():
            assert math.isfinite(value) and abs(value-ref["probabilities"][name]) < 1e-12
        for name, value in original["probabilities"].items():
            assert value == ref["probabilities"]["archived_"+name]
    assert len(cp_models.NAMES) == 22


def test_binding_rejects_unfrozen_correction_bundle(monkeypatch):
    monkeypatch.setitem(C, "calibration_models_sha256", "changed")
    with pytest.raises(ValueError, match="Calibration coefficients changed"):
        cp_models.calibration()


def test_expression_class_must_match_original_boundary():
    row = deepcopy(read(ROOT / "context/REPLAY_FEATURES.json")["forecasts"][0])
    row["current_pass"] = 1-row["current_pass"]
    with pytest.raises(ValueError, match="expression metadata"):
        cp_models.probabilities(row)


def test_fixed_models_and_six_directions_match_the_accepted_proposal():
    models = cp_models.calibration()
    assert all(m["gradient_max"] <= 1e-8 and m["ridge"] == .01 for m in models.values())
    proposal = read(ROOT / "context/NEXT_CANDIDATE.json")
    comparators = proposal["strongest_comparators"]
    assert cp_analysis.CANDIDATE == comparators["primary_candidate"] == "quadratic_successor64"
    assert list(cp_analysis.PRIMARY_RIVALS) == comparators["primary_equal_read_rivals"]
    assert len(cp_analysis.PRIMARY_RIVALS)+1 == proposal["rejection_criterion"]["primary_directions"] == 6
    assert C["blocks"] == proposal["held_out_change"]["proposed_blocks"] == list(range(24, 32))
    assert C["injury_levels"] == [18]


def test_expression_strata_recombine_with_equal_weights():
    rows, forecasts, outcomes, spec = unequal_fixture()
    result, audit = cp_analysis.analyze(rows, forecasts, outcomes, spec)
    assert audit["independent_expression_stratum_checks"] == 352
    for cell in result["injuries"]["18"].values():
        fail, passed = (cell["expression_strata"][str(s)] for s in (0, 1))
        for model in cp_models.NAMES:
            assert abs(fail["brier"][model]-.29) < 1e-12
            assert abs(passed["brier"][model]-.34) < 1e-12
            assert abs(cell["brier"][model]-(fail["brier"][model]+passed["brier"][model])/2) < 1e-12


def recovery_fixture():
    rows, forecasts, outcomes, spec = unequal_fixture()
    spec = dict(spec, scope="development")
    for y in outcomes:
        y["passed"] = 0
    for f in forecasts:
        if f["current_pass"]:
            f["probabilities"] = {m: .9 if m == cp_analysis.CANDIDATE else .1 for m in cp_models.NAMES}
        else:
            candidate, rival = (.1, .8) if f["regime"] == "matched" else (.2, .3)
            f["probabilities"] = {m: candidate if m == cp_analysis.CANDIDATE else rival for m in cp_models.NAMES}
    return rows, forecasts, outcomes, spec


def test_primary_uses_recovery_stratum_even_when_balanced_total_loses():
    rows, fs, ys, spec = recovery_fixture()
    result, _ = cp_analysis.analyze(rows, fs, ys, spec)
    assert result["fixed_panel_all_directions_positive"] is True
    for rival in cp_analysis.PRIMARY_RIVALS:
        assert abs(result["primary"]["matched:"+rival]["rival_minus_candidate"]-.63) < 1e-12
    assert abs(result["primary"][cp_analysis.INTERACTION]["rival_minus_candidate"]-.58) < 1e-12
    assert result["injuries"]["18"]["matched"]["contrasts"]["quadratic_direct64"]["rival_minus_candidate"] < 0
    assert result["inferential_verdict"] is None


def test_positive_matched_gains_do_not_rescue_failed_noise_interaction():
    rows, fs, ys, spec = recovery_fixture()
    for f in fs:
        if f["current_pass"] == 0 and f["regime"] == "independent":
            f["probabilities"][cp_analysis.CANDIDATE] = 0.
            f["probabilities"]["quadratic_direct64"] = 1.
    result, _ = cp_analysis.analyze(rows, fs, ys, spec)
    assert all(result["primary"]["matched:"+r]["rival_minus_candidate"] > 0 for r in cp_analysis.PRIMARY_RIVALS)
    assert abs(result["primary"][cp_analysis.INTERACTION]["rival_minus_candidate"]+.37) < 1e-12
    assert result["fixed_panel_all_directions_positive"] is False


@pytest.mark.parametrize("rival", cp_analysis.PRIMARY_RIVALS)
def test_any_nonpositive_direct_comparison_rejects_the_joint_direction(rival):
    rows, fs, ys, spec = recovery_fixture()
    for f in fs:
        if f["current_pass"] == 0 and f["regime"] == "matched":
            f["probabilities"][rival] = f["probabilities"][cp_analysis.CANDIDATE]
    result, _ = cp_analysis.analyze(rows, fs, ys, spec)
    assert result["primary"]["matched:"+rival]["rival_minus_candidate"] == 0.
    assert result["fixed_panel_all_directions_positive"] is False


def test_noise_interaction_and_leave_one_out_pair_individual_founders():
    rows, fs, ys, spec = recovery_fixture()
    for f in fs:
        i = spec["blocks"].index(f["block"])
        if f["current_pass"] == 0:
            f["probabilities"]["quadratic_direct64"] = (.4+.1*i) if f["regime"] == "matched" else (.6-.1*i)
    result, _ = cp_analysis.analyze(rows, list(reversed(fs)), list(reversed(ys)), spec)
    expected = [(.4+.1*i)**2-.1**2-((.6-.1*i)**2-.2**2) for i in range(4)]
    interaction = result["primary"][cp_analysis.INTERACTION]
    assert max(abs(a-b) for a,b in zip(interaction["block_gains"], expected, strict=True)) < 1e-12
    assert max(abs(v-(math.fsum(expected)-expected[i])/3) for i,v in enumerate(interaction["leave_one_founder_out"])) < 1e-12


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -.1, 1.1])
def test_invalid_probabilities_cannot_be_scored(bad):
    rows, fs, ys, spec = unequal_fixture()
    fs[0]["probabilities"][cp_analysis.CANDIDATE] = bad
    with pytest.raises(ValueError, match="probability"):
        cp_analysis.analyze(rows, fs, ys, spec)


def test_full_four_worker_measurement_timing_includes_wave_barrier(tmp_path):
    tasks, refs = [], []
    for block in C["qualification_blocks"]:
        folder = tmp_path / f"n18_b{block}"
        folder.mkdir()
        ledger.atomic_json(folder / "RESOURCES.json", dict(wall_seconds=10.))
        tasks.append(dict(kind="measure", injury=18))
        refs.append(dict(path=folder.name))
    assert len(tasks) == C["resources"]["workers"] == 4
    assert it_run.full_unit_timing(tmp_path, tasks, refs, [35.]) == {"18": 35.}
    with pytest.raises(ValueError, match="Incomplete"):
        it_run.full_unit_timing(tmp_path, tasks, refs, [])


@pytest.mark.parametrize("case", ["workers", "missing", "nonfinite"])
def test_resource_gate_rejects_mismatched_or_missing_timing(case):
    benchmark = dict(workers=4, cases=8)
    measurement, future = {"18": 250.}, {"18": 60.}
    if case == "workers":
        benchmark["workers"] = 8
    elif case == "missing":
        future.pop("18")
    else:
        measurement["18"] = float("nan")
    with pytest.raises(ValueError):
        it_run.timing_gate(benchmark, measurement, future)


def test_combined_cap_reserves_completion_and_includes_qualification():
    timing = dict(status="PASS", projected_seconds=1785.3587091271766)
    result = it_run.combined_budget_gate(500., timing)
    assert abs(result["projected_combined_seconds"]-2405.3587091271766) < 1e-10
    assert result["qualification_hard_seconds"]+result["target_hard_seconds"] == result["combined_hard_seconds"] == 3600
    with pytest.raises(ValueError, match="Combined"):
        it_run.combined_budget_gate(500., dict(status="PASS", projected_seconds=2581.))


@pytest.mark.parametrize("bad", [901., 0., -1., float("inf"), float("nan")])
def test_bad_qualification_time_cannot_admit_target(bad):
    with pytest.raises(ValueError, match="Qualification exceeded"):
        it_run.combined_budget_gate(bad, dict(status="PASS", projected_seconds=1800.))


def test_report_exposes_primary_scope_comparators_and_costs():
    rows, forecasts, outcomes, spec = unequal_fixture()
    result, _ = cp_analysis.analyze(rows, forecasts, outcomes, spec)
    costs = dict(primary_native_reads=7552, flat_native_reads=768, worker_cpu_seconds=0.,
                 candidate_first_seal_cpu_seconds=0.)
    model_costs = {m: dict(cpu_seconds=0., source="test") for m in ("direct8", "direct64", "successor32")}
    report = cp_analysis.report(result, costs, model_costs)
    assert all(text in report for text in ("six comparisons", "quadratic_successor64", "founders24..31",
                                          "disposable", "128 primary", "44 scientific fits", "zero fitting"))
    assert all(r in report for r in cp_analysis.PRIMARY_RIVALS)


def test_qualification_reduction_keeps_all_scientific_repeats_and_conditions():
    q, d = common.specification("qualification"), common.specification("development")
    assert q["repeats"] == [0, 3] and d["repeats"] == [0, 1, 2, 3]
    assert q["blocks"] == [-4, -3, -2, -1] and d["blocks"] == list(range(24, 32))
    assert q["injuries"] == d["injuries"] == [18]
    assert q["regimes"] == d["regimes"] == ["matched", "independent"]
    assert 4*len(d["blocks"])*len(d["regimes"])*len(d["repeats"]) == 256
    assert len(q["blocks"])*len(q["repeats"]) == 8


def test_two_repeats_cannot_be_accepted_as_a_complete_scientific_panel():
    rows, forecasts, outcomes, spec = unequal_fixture()
    scientific_spec = dict(spec, scope="development", repeats=[0, 1, 2, 3])
    with pytest.raises(ValueError, match="Incomplete candidate outcome panel"):
        cp_analysis.analyze(rows, forecasts, outcomes, scientific_spec)


def test_disposable_streams_versioned_and_target_streams_preserved():
    import it_forcing
    import numpy as np
    previous = read(ROOT / "context/QUALIFICATION_AMENDMENT_V2.json")
    assert previous["scientific"]["target_forcing_namespace_changed"] is False
    seen = []
    try:
        for scope in ("qualification", "benchmark", "development"):
            configured = common.configure(scope, 18)
            suffix = "development" if scope == "development" else scope+"_v2"
            expected_ns = f"{C['namespace']}/{suffix}/injury_18"
            assert configured["probe_namespace"] == expected_ns+"/probe"
            assert configured["future_namespace"] == expected_ns+"/future"
            for rep in range(4):
                stage = common.parent.C["stage"]+f"/replicate_{rep}"
                actual = it_forcing.random(configured["future_namespace"], stage,
                                            [24, "exact_rewrite", 0, 0], 33, "evaluation", "forcing").bytes(32)
                seen.append(actual)
                if scope == "development":
                    import hashlib, json
                    payload = [f"{C['namespace']}/development/injury_18/future",stage,
                               24,"exact_rewrite",0,0,33,"evaluation","forcing"]
                    seed = int.from_bytes(hashlib.sha256(json.dumps(payload,separators=(",", ":")).encode()).digest()[:16],"little")
                    expected = np.random.Generator(np.random.PCG64(seed)).bytes(32)
                    assert actual == expected
        assert len(seen) == len(set(seen)) == 12
    finally:
        common.configure("qualification",18)


def test_timeout_timings_are_floors_even_if_new_samples_are_faster():
    diagnosis = read(ROOT / "context/QUALIFICATION_V1_TIMING_DIAGNOSIS.json")["timing_diagnostic"]
    timing = it_run.timing_gate(dict(workers=4,cases=8),{"18":100.},{"18":20.})
    retained = timing["retained_full_unit_seconds"]["18"]
    assert retained["measurement"] == diagnosis["measured_full_measurement_wave_seconds"]
    assert retained["future"] == diagnosis["observed_max_completed_future_wave_seconds"]
    assert C["timing"]["multiplier"] == 1.5
    assert abs(timing["projected_seconds"]+120-2681.5173644931056) < 1e-10
