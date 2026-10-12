from concurrent.futures import Future
from copy import deepcopy
from dataclasses import asdict
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from laws_confirmation import l22_backup_free_feedback as study


@pytest.fixture(scope="module")
def checker():
    path = Path(__file__).resolve().parents[1] / "scripts/audit_l22_backup_free_feedback_outputs.py"
    spec = importlib.util.spec_from_file_location("l22_feedback_checker_tests", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def example():
    cfg = study.source.Config(replicates=1, settle=4, imprint=8, sweeps=12, times=(0, 1, 4, 12))
    ctx = study.source.context(40081, cfg)
    result, artifacts = study.experiment(ctx)
    return ctx, result, artifacts


def test_fresh_registry_and_functional_contract(checker):
    contract = study.contract()
    assert study.TISSUES == tuple(range(30008, 30024))
    assert len(study.ARMS) == 10 and len(study.PROBES) == 13
    assert contract["recovery_lives"] == 2560 and contract["assay_lives"] == 3328
    assert contract["workers"] == 4 and contract["minimum_positive_tissues"] == 12
    assert contract["quantiles"] == [.05 / 6, 1 - .05 / 6]
    assert all(study.MODES[a].reference == "zero" for a in study.ARMS if a != "backup")
    checker.audit.close(contract["modes"], checker.modes())
    checker.audit.close(json.loads(json.dumps(contract["config"])), checker.CFG)
    assert contract["law_verdict_changes"] == 0


def test_source_anchors_replays_and_local_routing(example):
    ctx, result, artifacts = example
    assert result["passes"] and all(v is True for v in result["gates"].values())
    assert len(artifacts) == 26
    assert len(study.source.MODES) == 18 and study.source.CONFIG.times == (0, 50, 250, 500, 1000)
    for s in ctx["config"].times:
        for k in ("V", "ema", "R"):
            np.testing.assert_array_equal(artifacts["recovery_fixed_damaged_reader"][f"s{s}_{k}"],
                                          artifacts["recovery_writer_off"][f"s{s}_{k}"])


def test_fixed_reader_separates_new_writing_from_applied_bias(example):
    ctx, _, artifacts = example
    b, parent = artifacts["boundary"], artifacts["parent"]
    mode = study.MODES["fixed_damaged_reader"]
    initial = study.source.initial_state(ctx, parent, {k: b[f"kept_{k}"] for k in study.KEYS},
                                        b["scrambled_V"], b["damaged_theta"], study.engine_mode(mode))
    native = ctx["native"].copy()
    local, reader = study.reader_context(ctx, initial, mode)
    assert local is not ctx and not reader.flags.writeable
    with pytest.raises(ValueError):
        reader.flat[0] = 0.
    changed = study.source.base.state_copy(initial)
    changed["theta"] = -changed["theta"]
    output = study.source.recover(local, changed, study.engine_mode(mode), parent, b["fresh"])
    for s in ctx["config"].times:
        for k in ("V", "ema", "R"):
            np.testing.assert_array_equal(output["raw"][f"s{s}_{k}"], artifacts["recovery_fixed_damaged_reader"][f"s{s}_{k}"])
    assert not np.array_equal(output["final"]["theta"], artifacts["recovery_fixed_damaged_reader"]["s12_theta"])
    np.testing.assert_array_equal(ctx["native"], native)
    np.testing.assert_array_equal(artifacts["recovery_wrong_fixed_reader"]["fixed_reader"], study.source.donor(b["damaged_theta"], 1))
    with pytest.raises(ValueError, match="reader"):
        study.engine_mode(study.Mode(reader="unregistered"))


def save_example(tmp_path, example):
    ctx, result, artifacts = example
    for name, arrays in artifacts.items():
        study.source.base.atomic_npz(tmp_path / f"{name}.npz", arrays, tmp_path)
    return json.loads(json.dumps(result)), json.loads(json.dumps(asdict(ctx["config"])))


def test_entire_saved_cell_and_calibration_rescore(example, checker, tmp_path):
    result, cfg = save_example(tmp_path, example)
    checked = checker.check_tissue(tmp_path, result, cfg)
    assert len(checked["recovery"]) == 10 and len(checked["probe"]) == 13
    cal, arrays = study.source.calibration(example[0])
    for name, raw in arrays.items():
        study.source.base.atomic_npz(tmp_path / f"calibration_{name}.npz", raw, tmp_path)
    assert checker.audit.check_calibration(tmp_path, cal, cfg) == cal["positive_accuracy"]


@pytest.mark.parametrize("kind", ("fixed_reader", "damaged_theta", "theta_trace", "projection_scale", "reference_trace", "probe_theta", "probe_R"))
def test_independent_audit_rejects_tampering(kind, example, checker, tmp_path):
    ctx, result, artifacts = deepcopy(example)
    if kind == "damaged_theta":
        artifacts["boundary"][kind].flat[0] += .1
    elif kind == "probe_theta":
        artifacts["probe_loop"]["s1_theta"].flat[0] += .1
    elif kind == "probe_R":
        artifacts["probe_loop"]["s1_R"].flat[0] += .1
    else:
        artifacts["recovery_fixed_damaged_reader"][kind].flat[0] += .1
    saved, cfg = save_example(tmp_path, (ctx, result, artifacts))
    with pytest.raises(AssertionError):
        checker.check_tissue(tmp_path, saved, cfg)


def test_theta_only_packet_and_fresh_births(example):
    ctx, result, a = example
    for name in study.PROBES:
        raw = a[f"probe_{name}"]
        assert "fixed_reader" not in raw
        for key in ("V", "ema", "R"):
            np.testing.assert_array_equal(raw[f"s0_{key}"], study.source.assay_birth(ctx)[key])
        for s in ctx["config"].times:
            np.testing.assert_array_equal(raw[f"s{s}_theta"], raw["s0_theta"])
            assert np.all(raw[f"s{s}_R"] == 0.)
    assert result["probe"]["reader_off"]["12"]["mean"]["V_accuracy"] == .25
    for bad in (b"wrong", None, a["parent"], np.full((4, 16, 16), np.nan).tobytes()):
        with pytest.raises(ValueError):
            study.source.assay(ctx, bad)


def positive_rows():
    rows = []
    for tissue in study.TISSUES:
        values = {a: {"1000": {"mean": {"V_accuracy": .25}}} for a in study.PROBES}
        values["parent"]["1000"]["mean"]["V_accuracy"] = 1.
        values["loop"]["1000"]["mean"]["V_accuracy"] = .75
        rows.append({"tissue": tissue, "passes": True, "gates": {"checked": True}, "probe": values})
    return rows


def checked_rows(rows):
    return [{"tissue": r["tissue"], "probe": {a: {t: v["mean"] for t, v in times.items()} for a, times in r["probe"].items()}} for r in rows]


@pytest.mark.parametrize("failed,label", (
    (None, "BACKUP_FREE_RECIPROCAL_LOOP_SUPPORTED"),
    ("writer_off", "NO_QUALIFIED_BACKUP_FREE_BENEFIT"),
    ("theta_read_off", "BACKUP_FREE_WRITING_BENEFIT_ONLY"),
    ("fixed_damaged_reader", "DAMAGED_READER_ASSISTED_WRITING_SUPPORTED"),
))
def test_separate_hierarchical_endpoints(failed, label, checker):
    rows = positive_rows()
    if failed:
        for row in rows:
            row["probe"][failed]["1000"]["mean"]["V_accuracy"] = .75
    classified = study.classify(rows)
    assert classified["label"] == label
    checker.audit.close(classified, checker.adjudicate(checked_rows(rows)))
    assert all(type(c["supported"]) is bool for c in classified["co_primary"].values())


def test_twelve_tissues_required_and_parent_qualification():
    rows = positive_rows()
    for row in rows[-5:]:
        row["probe"]["writer_off"]["1000"]["mean"]["V_accuracy"] = .75
    result = study.classify(rows)
    primary = result["co_primary"]["readout_vs_writer_off"]
    assert primary["interval"][0] > 0 and primary["positive_tissues"] == 11 and primary["supported"] is False
    rows = positive_rows()
    rows[0]["probe"]["parent"]["1000"]["mean"]["V_accuracy"] = .25
    assert study.classify(rows)["label"] == "PARENT_THETA_NOT_READABLE"
    assert study.classify(rows[:-1])["label"] == "INVALID_STRUCTURAL_FAILURE"
    rows[0]["gates"]["checked"] = "True"
    assert study.classify(rows)["label"] == "INVALID_STRUCTURAL_FAILURE"


def test_calibration_boolean_and_strict_serialization(example, tmp_path):
    rows = [{"tissue": t, "passes": True, "gates": {"checked": True}, "positive_accuracy": 1.} for t in study.TISSUES]
    assert study.calibrated(rows) is True
    study.strict_json(tmp_path / "success.json", {"qualified": study.calibrated(rows), "result": example[1]}, tmp_path)
    assert json.loads((tmp_path / "success.json").read_text())["qualified"] is True
    for value in (np.bool_(True), np.int64(1), float("nan")):
        with pytest.raises((ValueError, TypeError)):
            study.strict_json(tmp_path / "bad.json", {"bad": value}, tmp_path)
        assert not (tmp_path / "bad.json").exists()
    rows[0]["positive_accuracy"] = .25
    assert study.calibrated(rows) is False


@pytest.mark.parametrize("qualified", (True, False))
def test_entire_successful_terminal_path_and_early_calibration_stop(qualified, tmp_path, monkeypatch, capsys):
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
    assert status["classification"] == ("BACKUP_FREE_RECIPROCAL_LOOP_SUPPORTED" if qualified else "INSTRUMENT_NOT_QUALIFIED")
    assert len(calls) == (32 if qualified else 16)
    assert (run / "COMPLETE").is_file() and not (run / "FAILED").exists()


def test_long_run_requires_detach_without_polling(tmp_path, monkeypatch, checker):
    for module, runner, verifier in ((study, study.run_study, "verify_prepared"), (checker, checker.run_audit, "verify")):
        run = tmp_path / "runs" / module.RUN_ID
        run.mkdir(parents=True)
        monkeypatch.setattr(module, verifier, lambda root: {"benchmark": {"must_detach": True, "projected_seconds": 901}})
        with pytest.raises(RuntimeError, match="detached"):
            runner(tmp_path)
        calls = []
        def spawn(command, **kwargs):
            calls.append((command, kwargs))
            return SimpleNamespace(pid=40081)  # Deliberately no poll/wait methods.
        monkeypatch.setattr(module.subprocess, "Popen", spawn)
        result = module.detach(tmp_path)
        assert result["polling_owner"] == "user" and calls[0][1]["start_new_session"]
        assert calls[0][1]["stdin"] == module.subprocess.DEVNULL
        with pytest.raises(FileExistsError):
            module.detach(tmp_path)


def test_prepared_code_and_parameters_are_immutable(tmp_path, monkeypatch):
    run = tmp_path / "runs" / study.RUN_ID
    run.mkdir(parents=True)
    input_file = tmp_path / "source.txt"
    study.atomic_text(input_file, "frozen", tmp_path)
    study.strict_json(study.benchmark_path(tmp_path), {"passes": True}, tmp_path)
    monkeypatch.setattr(study, "input_paths", lambda: [input_file])
    hashes = {str(p): study.sha256_file(p) for p in (input_file, study.benchmark_path(tmp_path))}
    manifest = study.contract() | {"input_sha256": hashes, "hash_contract": study.canonical_digest(hashes)}
    study.strict_json(run / "MANIFEST.json", manifest, tmp_path)
    study.strict_json(run / "STATUS.json", {"status": "PREPARED"}, tmp_path)
    assert study.verify_prepared(tmp_path)["workers"] == 4
    study.strict_json(run / "MANIFEST.json", manifest | {"minimum_positive_tissues": 11}, tmp_path)
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
    with pytest.raises(RuntimeError, match="runtime/storage"):
        study.run_study(tmp_path)
    assert (run / "FAILED").is_file() and not (run / "COMPLETE").exists()
    with pytest.raises(AssertionError):
        checker.source_info(tmp_path)


def test_independent_audit_successful_publication(tmp_path, monkeypatch, checker):
    run = tmp_path / "runs" / checker.RUN_ID
    run.mkdir(parents=True)
    rows = positive_rows()
    checked = {r["tissue"]: r for r in checked_rows(rows)}
    calibrations = [{"tissue": t, "passes": True, "gates": {"checked": True}, "positive_accuracy": 1.} for t in study.TISSUES]
    source = {"calibrations": calibrations, "results": rows, "calibration_qualified": True,
              "classification": study.classify(rows)}
    monkeypatch.setattr(checker, "verify", lambda root: {"benchmark": {"must_detach": False}, "input_sha256": {"mock": "hash"}})
    monkeypatch.setattr(checker, "verify_hashes", lambda hashes: True)
    monkeypatch.setattr(checker, "runtime", lambda root: [0, 1, 2, 3])
    monkeypatch.setattr(checker, "source_info", lambda root: (source, [139, 482]))
    monkeypatch.setattr(checker.audit, "check_calibration", lambda directory, saved, cfg: 1.)
    monkeypatch.setattr(checker, "check_tissue", lambda directory, saved, cfg: checked[saved["tissue"]])
    study.atomic_text(tmp_path / "outputs" / checker.RUN_ID / "input_hashes.sha256", "mock input evidence\n", tmp_path)
    for result, cal in zip(rows, calibrations):
        directory = tmp_path / "outputs" / study.RUN_ID / f"tissue_{result['tissue']}"
        study.strict_json(directory / "experiment.json", result, tmp_path)
        study.strict_json(directory / "calibration.json", cal, tmp_path)
    assert checker.run_audit(tmp_path) == 0
    status = json.loads((run / "STATUS.json").read_text())
    record = json.loads((tmp_path / "outputs" / checker.RUN_ID / "rescore.json").read_text())
    assert status["status"] == "COMPLETE" and status["new_simulations"] == 0
    assert record["recovery_batches_checked"] == 160 and record["assay_batches_checked"] == 208
    assert record["batch_writer_updates_checked"] == 160000
    assert record["classification"] == study.classify(rows)
    assert (run / "COMPLETE").is_file() and not (run / "FAILED").exists()
