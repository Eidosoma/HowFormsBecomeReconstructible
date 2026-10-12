from concurrent.futures import Future
from copy import deepcopy
from dataclasses import asdict, replace
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from laws_confirmation import l22_fixed_record_readout as study


@pytest.fixture(scope="module")
def checker():
    path = Path(__file__).resolve().parents[1] / "scripts/audit_l22_fixed_record_readout_outputs.py"
    spec = importlib.util.spec_from_file_location("l22_readout_checker_tests", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def example():
    cfg = study.Config(parents=1, draws=2, sweeps=8, times=(0, 1, 8))
    ctx = study.context(40091, cfg)
    packets = study.synthetic_packets(ctx, cfg)
    result, arrays = study.experiment(ctx, packets, cfg)
    cal, cal_arrays = study.calibration(ctx, cfg)
    return ctx, cfg, packets, result, arrays, cal, cal_arrays


def save_example(tmp_path, example):
    _, cfg, _, result, arrays, cal, cal_arrays = example
    output, parent = tmp_path / "new", tmp_path / "old"
    for name, raw in arrays.items():
        study.source.base.atomic_npz(output / f"{name}.npz", raw, tmp_path)
    for name, raw in cal_arrays.items():
        study.source.base.atomic_npz(output / f"calibration_{name}.npz", raw, tmp_path)
    mapping = {"damaged": ("boundary", "damaged_theta"), "fixed": ("recovery_fixed_damaged_reader", "s1000_theta"),
               "loop": ("recovery_loop", "s1000_theta"), "parent": ("parent", "theta")}
    for name, (filename, key) in mapping.items():
        study.source.base.atomic_npz(parent / f"{filename}.npz", {key: arrays["packets"][name]}, tmp_path)
        old_name = "fixed_damaged_reader" if name == "fixed" else name
        study.source.base.atomic_npz(parent / f"probe_{old_name}.npz", arrays[f"legacy_{name}"], tmp_path)
    return output, parent, json.loads(json.dumps(result)), json.loads(json.dumps(asdict(cfg))), cal


def test_contract_counts_source_unchanged_and_equal_tissue_units(checker):
    c = study.contract()
    assert study.TISSUES == tuple(range(30008, 30024)) and len(study.ARMS) == 6
    assert c["scientific_readout_lives"] == 24576
    assert c["scientific_readout_lives"] + c["calibration_lives_including_replay"] + c["integrity_readout_lives"] == 41984
    assert c["new_training_lives"] == c["law_verdict_changes"] == 0
    assert c["minimum_positive_tissues"] == 12 and c["workers"] == 4
    assert study.prior.CONFIG.times == (0, 1, 50, 250, 500, 1000)
    assert study.source.CONFIG.times == (0, 50, 250, 500, 1000)
    checker.common.close(json.loads(json.dumps(c["config"])), checker.CFG)


def test_repetition_birth_pairing_and_distinct_namespace(example):
    ctx, cfg, packets, result, arrays, _, _ = example
    assert result["passes"] is True and len(arrays) == 11
    assert study.RNG(ctx["index"], "assay_birth", 1).digest() != study.source.RNG(ctx["index"], "assay_birth", 1).digest()
    loop = arrays["readout_loop"]
    expanded = study.expand(packets["loop"], cfg)
    np.testing.assert_array_equal(expanded[::2], expanded[1::2])
    assert not np.array_equal(loop["s0_V"][0], loop["s0_V"][1])
    for name in study.ARMS:
        raw = arrays[f"readout_{name}"]
        for key in ("V", "ema", "R"):
            np.testing.assert_array_equal(raw[f"s0_{key}"], loop[f"s0_{key}"])
        for s in cfg.times:
            np.testing.assert_array_equal(raw[f"s{s}_theta"], raw["s0_theta"])
            assert np.all(raw[f"s{s}_R"] == 0.)


def test_new_wrapper_native_first_step_and_legacy_replay(example):
    ctx, cfg, packets, _, arrays, _, _ = example
    raw = arrays["readout_loop"]
    native = ctx["api"]["blueprint_step"](raw["s0_V"].copy(), raw["s0_ema"].copy(), raw["s0_R"].copy(), raw["s0_theta"].copy(),
        ctx["tissue"], ctx["ladder"], replace(ctx["bp"], rho=0.), "T", study.RNG(ctx["index"], "assay", cfg.parents * cfg.draws), c_m=0.)
    for key, value in zip(("V", "ema", "R"), native):
        np.testing.assert_array_equal(raw[f"s1_{key}"], value)
    for name in study.PACKETS:
        original = study.source.assay(ctx, packets[name])
        for s in cfg.times:
            for key in study.KEYS:
                np.testing.assert_array_equal(arrays[f"legacy_{name}"][f"s{s}_{key}"], original["raw"][f"s{s}_{key}"])
    with pytest.raises(ValueError, match="exactly one"):
        study.assay(ctx, packets["loop"], cfg, legacy=True)


@pytest.mark.parametrize("bad", (None, {}, b"bad", np.full((4, 16, 16), np.nan).tobytes()))
def test_only_finite_theta_bytes_allowed(bad):
    with pytest.raises(ValueError):
        study.expand(bad, study.Config(parents=1))


def test_entire_saved_cell_calibration_and_off_alias(example, checker, tmp_path):
    output, parent, saved, cfg, cal = save_example(tmp_path, example)
    checked = checker.check_tissue(output, parent, saved, cfg)
    checker.common.close(checked["arms"], saved["arms"])
    assert checker.check_calibration(output, cal, cfg) == cal["positive_accuracy"]


@pytest.mark.parametrize("kind", ("birth", "theta", "R", "correctness", "scores", "variance", "legacy", "wrong"))
def test_independent_audit_rejects_tampering(kind, example, checker, tmp_path):
    values = deepcopy(example)
    arrays, saved = values[4], values[3]
    if kind == "variance":
        saved["arms"]["loop"]["within_record_variance"] += .1
    else:
        name, key = {"birth": ("readout_loop", "s0_V"), "theta": ("readout_loop", "s1_theta"),
            "R": ("readout_loop", "s1_R"), "correctness": ("readout_loop", "correctness"),
            "scores": ("readout_loop", "scores"), "legacy": ("legacy_loop", "s0_V"),
            "wrong": ("readout_wrong", "s1_V")}[kind]
        arrays[name][key].flat[0] += .1
    output, parent, saved, cfg, _ = save_example(tmp_path, values)
    with pytest.raises(AssertionError):
        checker.check_tissue(output, parent, saved, cfg)


def test_fractional_ties_and_exact_variance_decomposition(example, checker):
    ctx, cfg = example[:2]
    fields = np.repeat(ctx["codes"], 2, axis=0)
    fields[1] = ctx["codes"][1]
    expected = [1., 0., 1., 1., 1., 1., 1., 1.]
    m, raw = study.measure(ctx, fields, cfg)
    np.testing.assert_array_equal(raw["correctness"].ravel(), expected)
    assert m["varying_records"] == 1 and m["always_correct_records"] == 3
    assert m["within_record_variance"] == .0625 and m["between_record_variance"] == .046875
    checker.common.close(m, checker.measure(fields, asdict(cfg))[0])
    tied, raw = study.measure(ctx, np.zeros_like(fields), cfg)
    assert tied["accuracy"] == .25 and tied["total_variance"] == 0.
    assert np.all(raw["probabilities"] == .25)


def positive_rows(loop=.75, fixed=.5):
    return [{"tissue": t, "passes": True, "gates": {"checked": True},
             "arms": {a: {"accuracy": 1. if a == "parent" else loop if a == "loop" else fixed if a == "fixed" else .25}
                      for a in study.ARMS}} for t in study.TISSUES]


@pytest.mark.parametrize("loop,fixed,label", (
    (.75, .5, "LIVE_FEEDBACK_RECORD_RELIABILITY_SUPPORTED"),
    (.75, .75, "LIVE_WRITTEN_RECORD_RELIABILITY_SUPPORTED"),
    (.25, .75, "FIXED_READER_RECORD_RELIABILITY_ONLY"),
    (.25, .25, "NO_QUALIFIED_RECORD_RELIABILITY_BENEFIT")))
def test_separate_endpoints_and_independent_adjudication(loop, fixed, label, checker):
    rows = positive_rows(loop, fixed)
    result = study.classify(rows)
    assert result["label"] == label
    checker.common.close(result, checker.adjudicate(rows))
    assert all(type(v["supported"]) is bool for v in result["co_primary"].values())


def test_twelve_tissues_parent_qualification_and_invalid_structure():
    rows = positive_rows()
    for row in rows[-5:]:
        row["arms"]["damaged"]["accuracy"] = .75
    c = study.classify(rows)["co_primary"]["loop_vs_damaged"]
    assert c["interval"][0] > 0 and c["positive_tissues"] == 11 and c["supported"] is False
    rows[0]["arms"]["parent"]["accuracy"] = .25
    assert study.classify(rows)["label"] == "PARENT_THETA_NOT_READABLE"
    assert study.classify(rows[:-1])["label"] == "INVALID_STRUCTURAL_FAILURE"
    rows[0]["gates"]["checked"] = "True"
    assert study.classify(rows)["label"] == "INVALID_STRUCTURAL_FAILURE"


def test_calibration_and_strict_json(example, tmp_path):
    rows = [{"tissue": t, "passes": True, "gates": {"checked": True}, "positive_accuracy": 1.} for t in study.TISSUES]
    assert study.calibrated(rows) is True
    study.strict_json(tmp_path / "good.json", {"result": example[3], "calibrated": study.calibrated(rows)}, tmp_path)
    for value in (np.bool_(True), np.int64(1), float("nan")):
        with pytest.raises((TypeError, ValueError)):
            study.strict_json(tmp_path / "bad.json", {"bad": value}, tmp_path)
        assert not (tmp_path / "bad.json").exists()
    rows[0]["positive_accuracy"] = .25
    assert study.calibrated(rows) is False


@pytest.mark.parametrize("qualified", (True, False))
def test_successful_terminal_path_and_early_stop(qualified, tmp_path, monkeypatch, capsys):
    run = tmp_path / "runs" / study.RUN_ID
    run.mkdir(parents=True)
    monkeypatch.setattr(study, "verify_prepared", lambda root: {"benchmark": {"must_detach": False}, "input_sha256": {"mock": "hash"}})
    monkeypatch.setattr(study.source, "runtime", lambda: {"passes": True})
    monkeypatch.setattr(study.source, "disk_preflight", lambda root: {"passes": True})
    monkeypatch.setattr(study.source.base, "verify_hashes", lambda hashes: True)
    rows, calls = {r["tissue"]: r for r in positive_rows()}, []
    class Pool:
        def __init__(self, **kwargs):
            assert kwargs["max_workers"] == 4
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def submit(self, fn, index, root_text, stage):
            calls.append(stage)
            future = Future()
            if stage == "calibration":
                future.set_result({"tissue": index, "passes": True, "gates": {"checked": True}, "positive_accuracy": 1. if qualified else .25})
            else:
                assert qualified
                future.set_result(rows[index])
            return future
    monkeypatch.setattr(study, "ProcessPoolExecutor", Pool)
    assert study.run_study(tmp_path) == 0
    status = json.loads((run / "STATUS.json").read_text())
    assert json.loads(capsys.readouterr().out) == status
    assert status["status"] == "COMPLETE" and status["calibration_qualified"] is qualified
    assert status["completed_tissues"] == (16 if qualified else 0)
    assert status["classification"] == ("LIVE_FEEDBACK_RECORD_RELIABILITY_SUPPORTED" if qualified else "INSTRUMENT_NOT_QUALIFIED")
    assert len(calls) == (32 if qualified else 16)
    assert (run / "COMPLETE").is_file() and not (run / "FAILED").exists()


def test_long_runs_require_detach_never_poll(tmp_path, monkeypatch, checker):
    for module, runner, verifier in ((study, study.run_study, "verify_prepared"), (checker, checker.run_audit, "verify")):
        run = tmp_path / "runs" / module.RUN_ID
        run.mkdir(parents=True)
        monkeypatch.setattr(module, verifier, lambda root: {"benchmark": {"must_detach": True, "projected_seconds": 901}})
        with pytest.raises(RuntimeError, match="detached"):
            runner(tmp_path)
        calls = []
        def spawn(command, **kwargs):
            calls.append((command, kwargs))
            return SimpleNamespace(pid=40091)  # Deliberately no poll/wait methods.
        monkeypatch.setattr(module.subprocess, "Popen", spawn)
        result = module.detach(tmp_path)
        assert result["polling_owner"] == "user" and calls[0][1]["start_new_session"]
        assert calls[0][1]["stdin"] == module.subprocess.DEVNULL
        with pytest.raises(FileExistsError):
            module.detach(tmp_path)


def test_prepared_code_and_draws_are_immutable(tmp_path, monkeypatch):
    run = tmp_path / "runs" / study.RUN_ID
    run.mkdir(parents=True)
    input_file = tmp_path / "source.txt"
    study.atomic_text(input_file, "frozen", tmp_path)
    study.strict_json(study.benchmark_path(tmp_path), {"passes": True}, tmp_path)
    monkeypatch.setattr(study, "input_paths", lambda root: [input_file])
    hashes = {str(p): study.sha256_file(p) for p in (input_file, study.benchmark_path(tmp_path))}
    manifest = study.contract() | {"input_sha256": hashes, "hash_contract": study.canonical_digest(hashes)}
    study.strict_json(run / "MANIFEST.json", manifest, tmp_path)
    study.strict_json(run / "STATUS.json", {"status": "PREPARED"}, tmp_path)
    assert study.verify_prepared(tmp_path)["workers"] == 4
    changed = deepcopy(manifest)
    changed["config"]["draws"] = 17
    study.strict_json(run / "MANIFEST.json", changed, tmp_path)
    with pytest.raises(RuntimeError, match="contract changed"):
        study.verify_prepared(tmp_path)
    study.strict_json(run / "MANIFEST.json", manifest, tmp_path)
    study.atomic_text(input_file, "changed", tmp_path)
    with pytest.raises(RuntimeError, match="contract changed"):
        study.verify_prepared(tmp_path)
    with pytest.raises(FileExistsError):
        study.prepare(tmp_path)


def test_runtime_failure_and_failed_source_refusal(tmp_path, monkeypatch, checker):
    run = tmp_path / "runs" / study.RUN_ID
    run.mkdir(parents=True)
    monkeypatch.setattr(study, "verify_prepared", lambda root: {"benchmark": {"must_detach": False}})
    monkeypatch.setattr(study.source, "runtime", lambda: {"passes": False})
    with pytest.raises(AssertionError):
        study.run_study(tmp_path)
    assert (run / "FAILED").is_file() and not (run / "COMPLETE").exists()
    with pytest.raises(AssertionError):
        checker.source_info(tmp_path)
    old = tmp_path / "runs" / study.SOURCE_ID
    study.strict_json(old / "STATUS.json", {"status": "FAILED"}, tmp_path)
    with pytest.raises(AssertionError):
        study.source_info(tmp_path)


@pytest.mark.parametrize("qualified", (True, False))
def test_independent_audit_successful_terminal_paths(qualified, tmp_path, monkeypatch, checker):
    run = tmp_path / "runs" / checker.RUN_ID
    run.mkdir(parents=True)
    rows = positive_rows() if qualified else []
    checked = {r["tissue"]: r for r in rows}
    cals = [{"tissue": t, "passes": True, "gates": {"checked": True}, "positive_accuracy": 1. if qualified else .25} for t in study.TISSUES]
    source = {"calibrations": cals, "results": rows, "calibration_qualified": qualified,
              "classification": study.classify(rows) if qualified else {"label": "INSTRUMENT_NOT_QUALIFIED"}}
    monkeypatch.setattr(checker, "verify", lambda root: {"benchmark": {"must_detach": False}, "input_sha256": {"mock": "hash"}})
    monkeypatch.setattr(checker, "verify_hashes", lambda hashes: True)
    monkeypatch.setattr(checker, "runtime", lambda root: [0, 1, 2, 3])
    monkeypatch.setattr(checker, "source_info", lambda root: (source, [639, 242 if qualified else 50]))
    monkeypatch.setattr(checker, "check_calibration", lambda directory, saved, cfg: saved["positive_accuracy"])
    monkeypatch.setattr(checker, "check_tissue", lambda directory, parent, saved, cfg: checked[saved["tissue"]])
    study.atomic_text(tmp_path / "outputs" / checker.RUN_ID / "input_hashes.sha256", "mock input evidence\n", tmp_path)
    for cal in cals:
        directory = tmp_path / "outputs" / study.RUN_ID / f"tissue_{cal['tissue']}"
        study.strict_json(directory / "calibration.json", cal, tmp_path)
        if qualified:
            study.strict_json(directory / "experiment.json", checked[cal["tissue"]], tmp_path)
    assert checker.run_audit(tmp_path) == 0
    status = json.loads((run / "STATUS.json").read_text())
    record = json.loads((tmp_path / "outputs" / checker.RUN_ID / "rescore.json").read_text())
    assert status["status"] == "COMPLETE" and status["new_simulations"] == 0
    assert record["scientific_readout_batches_checked"] == (96 if qualified else 0)
    assert record["historical_readout_batches_checked"] == (64 if qualified else 0)
    assert record["calibration_batches_checked"] == 32
    assert (run / "COMPLETE").is_file() and not (run / "FAILED").exists()
