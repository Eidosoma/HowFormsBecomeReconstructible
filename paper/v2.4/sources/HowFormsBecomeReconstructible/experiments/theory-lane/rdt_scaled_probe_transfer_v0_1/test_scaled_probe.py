"""Saved-prediction replay, no fitting, strata and resource rejection checks."""
from copy import deepcopy
import math
import pytest

from it_common import ROOT, C, ev, read, ledger
import cp_models
import cp_analysis
import ec_models
import it_run
from test_cheap_probe import unequal_fixture


def test_reproduce_every_saved_prediction_without_fitting(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("This continuation study must not fit models")
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


def test_correction_expression_class_must_match_original_boundary():
    row = deepcopy(read(ROOT / "context/REPLAY_FEATURES.json")["forecasts"][0])
    row["current_pass"] = 1-row["current_pass"]
    with pytest.raises(ValueError, match="expression metadata"):
        cp_models.probabilities(row)


def test_correction_training_and_primary_direction_match_handoff():
    models = cp_models.calibration()
    assert all(m["gradient_max"] <= 1e-8 and m["ridge"] == .01 for m in models.values())
    expected = {(r["candidate"], r["rival"], r["noise"]) for r in read(ROOT / "context/NEXT_CANDIDATE.json")["primary"]}
    assert expected == {(cp_analysis.CANDIDATE, r, g) for r in cp_analysis.PRIMARY_RIVALS for g in C["regimes"]}
    assert len(expected) == 6 and cp_analysis.CANDIDATE == "scale_direct8"
    for injury in (12, 18, 24, 30, 36):
        for regime in C["regimes"]:
            assert ec_models.correction_functions(models["scale_direct8"], "scale", injury, regime)["C"] == 0


def test_expression_strata_recombine_with_equal_weights():
    rows, forecasts, outcomes, spec = unequal_fixture()
    result, audit = cp_analysis.analyze(rows, forecasts, outcomes, spec)
    assert audit["independent_expression_stratum_checks"] == 352
    for regimes in result["injuries"].values():
        for cell in regimes.values():
            fail, passed = (cell["expression_strata"][str(s)] for s in (0, 1))
            for model in cp_models.NAMES:
                assert abs(fail["brier"][model]-.29) < 1e-12
                assert abs(passed["brier"][model]-.34) < 1e-12
                assert abs(cell["brier"][model]-(fail["brier"][model]+passed["brier"][model])/2) < 1e-12


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -.1, 1.1])
def test_bad_fixed_probabilities_cannot_be_scored(bad):
    rows, forecasts, outcomes, spec = unequal_fixture()
    forecasts[0]["probabilities"]["scale_direct8"] = bad
    with pytest.raises(ValueError, match="probability"):
        cp_analysis.analyze(rows, forecasts, outcomes, spec)


def test_full_wave_timing_includes_startup_and_mixed_condition_barrier(tmp_path):
    tasks, refs = [], []
    for injury in (18, 30):
        for block in (-2, -1):
            folder = tmp_path / f"n{injury}_b{block}"
            folder.mkdir()
            ledger.atomic_json(folder / "RESOURCES.json", dict(wall_seconds=10.))
            tasks.append(dict(kind="measure", injury=injury))
            refs.append(dict(path=folder.name))
    assert it_run.full_unit_timing(tmp_path, tasks, refs, [35.]) == {"18": 35., "30": 35.}
    with pytest.raises(ValueError, match="Incomplete"):
        it_run.full_unit_timing(tmp_path, tasks, refs, [])


@pytest.mark.parametrize("case", ["workers", "missing", "nonfinite"])
def test_resource_gate_rejects_mismatched_or_missing_timing(case):
    benchmark = dict(workers=4, cases=8)
    measurement = {"18": 250., "30": 250.}
    future = {"18": 60., "30": 60.}
    if case == "workers":
        benchmark["workers"] = 8
    elif case == "missing":
        future.pop("18")
    else:
        measurement["30"] = float("nan")
    with pytest.raises(ValueError):
        it_run.timing_gate(benchmark, measurement, future)


def test_report_contains_costs_six_primary_comparisons_and_scope():
    rows, forecasts, outcomes, spec = unequal_fixture()
    result, _ = cp_analysis.analyze(rows, forecasts, outcomes, spec)
    costs = dict(primary_native_reads=7552, flat_native_reads=768, worker_cpu_seconds=0.,
                 candidate_first_seal_cpu_seconds=0.)
    model_costs = {m: dict(cpu_seconds=0., source="test") for m in ("direct8", "direct64", "successor32")}
    report = cp_analysis.report(result, costs, model_costs)
    assert all(text in report for text in ("six comparisons", "scale_direct8", "founders16..23",
                                          "disposable", "128 primary", "44 scientific fits", "zero fitting"))
