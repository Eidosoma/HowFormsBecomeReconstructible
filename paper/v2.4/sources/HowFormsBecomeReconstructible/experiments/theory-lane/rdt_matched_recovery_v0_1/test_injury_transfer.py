"""Contracts that change with the injury adapter, global barrier and pilot scope."""
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import time

import numpy as np
import pytest

import it_common as common
from it_common import C, P, MODELS, REGIMES, ev, read, ledger, identity
import it_forcing as forcing
import it_evidence as evidence
import it_analysis
import it_run
import it_worker
import probes
import futures


@pytest.fixture(autouse=True)
def restore_condition():
    common.configure("qualification", C["injury_levels"][0])
    yield
    common.configure("qualification", C["injury_levels"][0])


@pytest.mark.parametrize("future", [False, True])
@pytest.mark.parametrize("regime", ["matched", "independent"])
@pytest.mark.parametrize("purpose", ["writer", "evaluation"])
def test_24_cell_adapter_is_byte_identical_to_original(future, regime, purpose):
    ns = P["forcing"]["future_namespace" if future else "namespace"]
    original = forcing.ORIGINAL_FUTURE if future else forcing.ORIGINAL_PROBE
    args = ("compatibility", [-9, "exact_rewrite", 1, 0], 15, purpose, regime)
    expected = original(*args)
    actual = forcing.environment(ns, *args, 24)
    for old, new in zip(expected, actual, strict=True):
        assert old.shape == new.shape and old.dtype == new.dtype and old.tobytes() == new.tobytes()


@pytest.mark.parametrize("injury", C["injury_levels"])
@pytest.mark.parametrize("future", [False, True])
def test_declared_injury_and_paired_noise(injury, future):
    common.configure("qualification", injury)
    function = futures.environment if future else probes.environment
    args = ("test", [-2, "exact_rewrite", 0, 0], 3, "writer")
    matched = function(*args, "matched")
    independent = function(*args, "independent")
    assert int(matched[0].sum()) == injury
    assert not np.any(matched[0] & common.e.PORTS.any(axis=0))
    assert np.array_equal(matched[0], independent[0])
    assert np.array_equal(matched[1][0], independent[1][0])
    assert np.array_equal(matched[1][0], matched[1][1])
    assert np.array_equal(matched[2][:, 0], independent[2][:, 0])
    assert np.array_equal(matched[2][:, 0], matched[2][:, 1])
    assert not np.array_equal(independent[2][:, 0], independent[2][:, 1])


def test_seed_contract_matches_direct_independent_construction():
    ns = "one-declared-stream"
    args = ("stage", [-2, "exact_rewrite", 1, 0], 19, "evaluation", "injury")
    payload = [ns, args[0], *args[1], args[2], args[3], args[4]]
    seed = int.from_bytes(hashlib.sha256(json.dumps(payload, separators=(",", ":")).encode()).digest()[:16], "little")
    expected = np.random.Generator(np.random.PCG64(seed)).integers(0, 1000000, size=32)
    actual = forcing.random(ns, *args).integers(0, 1000000, size=32)
    assert np.array_equal(actual, expected)


def test_probe_future_repeats_and_injury_streams_are_distinct():
    values = []
    for scope in ("qualification", "benchmark", "development"):
        for injury in C["injury_levels"]:
            common.configure(scope, injury)
            for channel in ("namespace", "future_namespace"):
                for rep in range(4):
                    rng = forcing.random(P["forcing"][channel], f"stage/r{rep}", [-2, "h", 0, 0], 15, "writer", "forcing")
                    values.append(rng.bytes(32))
    assert len(values) == len(set(values))


@pytest.mark.parametrize("injury", [-1, 10000, 12.0])
def test_invalid_injury_is_rejected(injury):
    with pytest.raises(ValueError):
        forcing.mask_for("n", "s", [0], 0, "writer", injury)


def test_condition_change_preserves_reader_writer_coefficients_and_boundary_namespace():
    common.configure("qualification", C["injury_levels"][0])
    before = deepcopy(P)
    digest = ev.sha(common.PARENT / "qualified/FROZEN_MODELS.json")
    common.configure("development", C["injury_levels"][-1])
    for name in P:
        if name != "forcing":
            assert P[name] == before[name]
    for key in P["forcing"]:
        if key not in ("namespace", "future_namespace"):
            assert P["forcing"][key] == before["forcing"][key]
    assert digest == C["models_sha256"] == ev.sha(common.PARENT / "qualified/FROZEN_MODELS.json")


@pytest.fixture
def panel(tmp_path):
    root = tmp_path / "run"
    root.mkdir()
    spec = common.specification("qualification")
    ref = evidence.create_panel(root, spec)
    return root, spec, ref, evidence.panel(root, ref, spec)


def test_panel_contains_both_tasks_and_expression_classes(panel):
    root, spec, ref, plan = panel
    assert len(plan["rows"]) == 16
    for block in spec["blocks"]:
        rows, packets = evidence.source(root, plan, block, spec)
        assert {r["current_pass"] for r in rows} == {0, 1}
        assert {r["rule"] for r in rows} == {-1, 1}
        assert len(rows) == 4 and len({r["packet_sha256"] for r in rows}) == 4
        for state in (0, 1):
            assert {r["rule"] for r in rows if r["current_pass"] == state} == {-1, 1}
        assert all(p.shape == (2, 16, 16) for p in packets)


def test_development_panel_reuses_original_selected_eight_blocks(tmp_path):
    root = tmp_path / "development"
    root.mkdir()
    spec = common.specification("development")
    ref = evidence.create_panel(root, spec)
    plan = evidence.panel(root, ref, spec)
    origin = read(common.ROOT / "context/SOURCE_COHORT.json")
    assert plan["rows"] == [r for r in origin["rows"] if r["block"] in C["blocks"]]
    assert plan["blocks"] == C["blocks"]


@pytest.fixture
def saved_forecasts(panel, monkeypatch):
    root, spec, panel_ref, plan = panel
    refs = []
    for injury in spec["injuries"]:
        for block in spec["blocks"]:
            folder = root / f"units/measure/n{injury}_b{block}"
            folder.mkdir(parents=True)
            predictions = []
            rows = [r for r in plan["rows"] if r["block"] == block]
            for i, row in enumerate(rows):
                for regime in REGIMES:
                    case = folder / f"case_{i:02d}_{regime}"
                    case.mkdir()
                    forecast = dict(**row, regime=regime,
                                    fractions={m: None if m == "tt008" else .5 for m in MODELS},
                                    probabilities={m: .4 + .01 * j for j, m in enumerate(MODELS)})
                    ledger.atomic_json(case / "FORECAST.json", forecast)
                    order = ["successor32", "direct64"]
                    if (i + REGIMES.index(regime)) % 2:
                        order.reverse()
                    ledger.atomic_json(case / "ORDER.json", dict(order=order, packet_index=i))
                    predictions.append(dict(**forecast, injury=injury))
            ledger.atomic_json(folder / "FORECASTS.json", predictions)
            ledger.commit(folder, identity(spec, "measure", block=block, injury=injury),
                          dict(block=block, injury=injury, forecasts=predictions,
                               native_reads=len(predictions) * 128, flat_native_reads=len(predictions) * 4))
            refs.append(ledger.reference(root, folder))
    monkeypatch.setattr(evidence.fe_measurement, "check_saved", lambda folder, row, regime: read(folder / "FORECAST.json"))
    monkeypatch.setattr(evidence.it_forcing, "measurement_masks", lambda *args: 128)
    return root, spec, panel_ref, plan, refs


def test_global_seal_contains_all_conditions_and_five_models(saved_forecasts):
    root, spec, panel_ref, plan, refs = saved_forecasts
    ref = evidence.seal_forecasts(root, spec, panel_ref, refs)
    _, seal = evidence.check_seal(root, ref, spec)
    assert len(seal["forecasts"]) == 32
    assert all(set(f["probabilities"]) == set(MODELS) for f in seal["forecasts"])


def test_missing_founder_measurements_prevent_sealing(saved_forecasts):
    root, spec, panel_ref, plan, refs = saved_forecasts
    with pytest.raises(ValueError):
        evidence.seal_forecasts(root, spec, panel_ref, refs[:2])
    assert not (root / "forecast_seal").exists()


def test_existing_future_evidence_prevents_first_seal(saved_forecasts):
    root, spec, panel_ref, plan, refs = saved_forecasts
    (root / "units/future").mkdir()
    with pytest.raises(ValueError):
        evidence.seal_forecasts(root, spec, panel_ref, refs)


@pytest.mark.parametrize("damage", ["model", "duplicate", "wrong_injury", "boundary"])
def test_incomplete_or_changed_forecast_coverage_rejected(saved_forecasts, damage):
    root, spec, panel_ref, plan, refs = saved_forecasts
    forecasts = [f for ref in refs for f in read(root / ref["path"] / "FORECASTS.json")]
    if damage == "model":
        forecasts[0]["probabilities"].pop("direct8")
    elif damage == "duplicate":
        forecasts[-1] = forecasts[0]
    elif damage == "wrong_injury":
        forecasts[0]["injury"] = 24
    else:
        forecasts[0]["boundary"][0] += 1
    with pytest.raises(ValueError):
        evidence.check_coverage(plan["rows"], forecasts, spec)


def test_future_cannot_reach_native_dynamics_without_global_seal(panel, monkeypatch, tmp_path):
    root, spec, panel_ref, plan = panel
    called = []
    monkeypatch.setattr(it_worker.futures, "batch", lambda *a, **k: called.append(True))
    task = dict(run=str(root), spec=spec, replicate=0, injury=C["injury_levels"][0], block=-2,
                seal=dict(path="missing.json", sha256="missing", ref={}))
    with pytest.raises(ValueError):
        it_worker.future(tmp_path, task, common.Guard(root, time.time() + 30))
    assert called == []


def test_changed_seal_is_rejected(saved_forecasts):
    root, spec, panel_ref, plan, refs = saved_forecasts
    ref = evidence.seal_forecasts(root, spec, panel_ref, refs)
    path = root / ref["path"]
    path.write_text(path.read_text() + " ")
    with pytest.raises(ValueError):
        evidence.check_seal(root, ref, spec)


def analysis_fixture(saved_forecasts):
    root, spec, panel_ref, plan, refs = saved_forecasts
    forecasts = [f for ref in refs for f in read(root / ref["path"] / "FORECASTS.json")]
    outcomes = [dict(key=r["key"], regime=g, injury=n, replicate=rep,
                     passed=int((r["founder"] + rep) % 3 == 0))
                for n in spec["injuries"] for r in plan["rows"] for g in REGIMES for rep in spec["repeats"]]
    return spec, plan["rows"], forecasts, outcomes


def test_analysis_is_descriptive_and_matches_scalar_reduction(saved_forecasts):
    spec, rows, fs, ys = analysis_fixture(saved_forecasts)
    result, audit = it_analysis.analyze(rows, fs, ys, spec)
    assert audit["status"] == "PASS" and audit["independent_scalar_contrasts"] == 8
    assert result["inferential_verdict"] is None
    assert all(value["inferential_verdict"] is None for value in result["injuries"].values())
    encoded = json.dumps(result, allow_nan=False)
    assert '"decision"' not in encoded and '"SUPPORTED"' not in encoded
    assert result["outcomes"] == 64 and result["new_model_fits"] == 0


@pytest.mark.parametrize("damage", ["missing_repeat", "wrong_injury", "duplicate"])
def test_partial_or_wrong_condition_outcomes_never_get_scored(saved_forecasts, damage):
    spec, rows, fs, ys = analysis_fixture(saved_forecasts)
    if damage == "missing_repeat":
        ys.pop()
    elif damage == "wrong_injury":
        ys[0]["injury"] = 24
    else:
        ys[-1] = ys[0]
    with pytest.raises(ValueError):
        it_analysis.analyze(rows, fs, ys, spec)


def test_measurement_and_future_timing_each_can_close_the_bounded_gate():
    benchmark = dict(workers=4, cases=8)
    baseline = it_run.timing_gate(benchmark, {"18": 250.}, {"18": 60.})
    assert baseline["status"] == "PASS"
    assert abs(baseline["projected_seconds"] - C["timing"]["historical_projection_seconds"]) < 1e-10
    assert it_run.timing_gate(benchmark, {"18": 600.}, {"18": 60.})["status"] == "FAIL_NO_PILOT"
    assert it_run.timing_gate(benchmark, {"18": 250.}, {"18": 200.})["status"] == "FAIL_NO_PILOT"
    assert baseline["hard_wall_seconds"] == 2700 and baseline["preferred_seconds"] == 2700


def test_benchmark_has_eight_unique_tasks_and_all_four_blocks(panel):
    root, spec, ref, plan = panel
    tasks = it_run.benchmark_tasks(spec, ref)
    assert len(tasks) == len({it_run.task_name(t) for t in tasks}) == 8
    assert {t["injury"] for t in tasks} == set(C["injury_levels"])
    assert {t["regime"] for t in tasks} == set(REGIMES)
    assert {t["block"] for t in tasks} == {-4, -3, -2, -1}
    assert {t["packet_index"] for t in tasks} == {0, 1, 2, 3}
    assert {plan["rows"][spec["blocks"].index(t["block"])*4+t["packet_index"]]["rule"] for t in tasks} == {-1, 1}


def test_failed_qualification_cannot_admit_development(monkeypatch, tmp_path):
    monkeypatch.setattr(it_run, "verify_complete", lambda p: dict(
        scope="qualification", decision="QUALIFICATION_PASSED_TIMING_GATE_FAILED",
        timing=dict(status="FAIL_NO_PILOT"), development_outcomes=0))
    with pytest.raises(ValueError):
        it_run.qualification_binding(tmp_path)


def test_unqualified_development_failure_is_durable_and_launches_no_tasks(monkeypatch, tmp_path):
    monkeypatch.setattr(it_run, "verify_snapshot", lambda: 1)
    root = tmp_path / "failed"
    with pytest.raises(ValueError, match="matching successful qualification"):
        it_run.run(root, "development")
    assert read(root / "STATUS.json")["status"] == "FAILED"
    failure = read(root / "FAILED.json")
    assert failure["inferential_verdict"] is None and failure["automatic_retry"] is False
    assert not list((root / "tasks").glob("*"))
    assert not (root / "COMPLETE.json").exists()
