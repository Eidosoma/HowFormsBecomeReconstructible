from concurrent.futures import Future
from copy import deepcopy
from dataclasses import asdict
import importlib.util
import json
from pathlib import Path
import shutil
from types import SimpleNamespace

import numpy as np
import pytest

from laws_confirmation import l22_fresh_writing_replication as study


@pytest.fixture(scope="module")
def checker():
    path = Path(__file__).resolve().parents[1] / "scripts/audit_l22_fresh_writing_replication_outputs.py"
    spec = importlib.util.spec_from_file_location("l22_fresh_writing_tests_checker", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def cell(tmp_path_factory):
    root = tmp_path_factory.mktemp("fresh-writing-cell")
    cfg = study.source.Config(replicates=1, settle=4, imprint=8, sweeps=1000, times=(0, 1, 1000))
    rcfg = study.readout.Config(parents=1, draws=2, sweeps=1000, times=(0, 1, 1000))
    ctx = study.source.context(400101, cfg)
    cal, cal_arrays = study.calibration(ctx, rcfg)
    for name, raw in cal_arrays.items():
        study.save_arrays(root / name, raw, root, "calibration_")
        study.strict_json(root / name / "calibration.json", cal["legacy" if name == "writing" else "readout"], root)
    written, arrays = study.writing.experiment(ctx)
    study.save_writing(root / "writing", written, arrays, root)
    observed, raw = study.read_written(ctx, root / "writing", rcfg)
    study.save_arrays(root / "readout", raw, root)
    study.strict_json(root / "readout" / "experiment.json", observed, root)
    return root, cfg, rcfg, json.loads(json.dumps(written)), json.loads(json.dumps(observed)), cal


def reseal_test_cell(root, saved):
    wd = root / "writing"
    files = sorted(p for p in wd.glob("*.npz") if not p.name.startswith("calibration_")) + [wd / "experiment.json"]
    study.write_hash_manifest(files, wd / "writing_hashes.sha256", root)
    saved["writing_manifest_sha256"] = study.sha256_file(wd / "writing_hashes.sha256")
    study.strict_json(root / "readout" / "experiment.json", saved, root)


def test_fresh_registry_counts_and_unchanged_sources(checker):
    c = study.contract()
    assert study.TISSUES == tuple(range(30024, 30040))
    assert not set(study.TISSUES) & set(study.writing.TISSUES)
    assert not set(study.TISSUES) & set(study.readout.TISSUES)
    assert c["total_lives"] == sum(c[k] for k in ("parent_lives", "recovery_lives", "legacy_diagnostic_readouts",
        "legacy_calibration_lives", "writing_integrity_lives", "scientific_readout_lives", "readout_calibration_lives",
        "readout_replay_lives", "legacy_wrapper_replay_lives")) == 49920
    assert c["retained_scientific_packets_used"] == 0 and c["fresh_parent_replication"] is True
    assert c["minimum_positive_tissues"] == 12 and c["workers"] == 4
    assert c["qualified_output_hashes"] == 738 and c["unqualified_output_hashes"] == 98
    checker.common.close(json.loads(json.dumps(c["config"])), checker.CFG)
    checker.common.close(json.loads(json.dumps(c["readout_config"])), checker.RCFG)
    checker.common.close(c["modes"], checker.writing.modes())
    assert study.writing.CONFIG.times == (0, 1, 50, 250, 500, 1000)
    assert study.readout.CONFIG.draws == 16 and study.readout.SEEDS[0] == 20260908097201


def test_whole_current_parent_writing_readout_cell_independently_checks(cell, checker):
    root, cfg, rcfg, written, observed, cal = cell
    checked = checker.check_tissue(root, written, observed, json.loads(json.dumps(asdict(cfg))), json.loads(json.dumps(asdict(rcfg))))
    scores = checker.check_calibration(root, cal, json.loads(json.dumps(asdict(cfg))), json.loads(json.dumps(asdict(rcfg))))
    assert set(checked["writing"]["recovery"]) == set(study.writing.ARMS)
    assert len(checked["writing"]["probe"]) == 13 and len(checked["readout"]["arms"]) == 6
    assert set(scores) == {"legacy", "readout"}
    packets = study.load_written(root / "writing", cfg)
    assert len(packets) == 4 and all(type(p) is bytes and len(p) == 8192 for p in packets.values())
    assert observed["packet_origin"] == "current_fresh_writing_cell"
    assert len(list(root.rglob("*.*"))) == 46


@pytest.mark.parametrize("kind", ("birth", "theta", "scores", "writing_trace", "packet", "origin", "manifest", "parent"))
def test_independent_checker_rejects_consistently_rehashed_tampering(kind, cell, checker, tmp_path):
    original, cfg, rcfg, written, observed, _ = cell
    root = tmp_path / "cell"
    shutil.copytree(original, root)
    saved = deepcopy(observed)
    if kind == "origin":
        saved["packet_origin"] = "old_retained_packet"
    elif kind == "manifest":
        pass
    else:
        folder, name, key = {"birth": ("readout", "readout_loop", "s0_V"), "theta": ("readout", "readout_loop", "s1_theta"),
            "scores": ("readout", "readout_loop", "scores"), "writing_trace": ("writing", "recovery_loop", "theta_trace"),
            "packet": ("readout", "packets", "loop"), "parent": ("writing", "parent", "theta")}[kind]
        path = root / folder / f"{name}.npz"
        arrays = checker.common.arrays(path)
        arrays[key].flat[0] += .1
        study.source.base.atomic_npz(path, arrays, root)
    reseal_test_cell(root, saved)  # Do not let a stale hash alone catch a fabricated producer output.
    if kind == "manifest":
        saved["writing_manifest_sha256"] = "0" * 64
        study.strict_json(root / "readout" / "experiment.json", saved, root)
    with pytest.raises(AssertionError):
        checker.check_tissue(root, written, saved, json.loads(json.dumps(asdict(cfg))), json.loads(json.dumps(asdict(rcfg))))


def test_writing_loader_rejects_wrong_packet_hash_and_rebased_history(cell, checker, tmp_path):
    original, cfg, _, written, observed, _ = cell
    with pytest.raises(AssertionError):
        study.load_written(original / "writing", cfg, expected_tissue=400102)
    root = tmp_path / "cell"
    shutil.copytree(original, root)
    with pytest.raises(AssertionError):
        study.load_written(root / "writing", cfg)  # Manifest still names the other cell.
    saved_writing = deepcopy(written)
    saved_writing["probe_packet_hashes"]["loop"] = "0" * 64
    study.strict_json(root / "writing" / "experiment.json", saved_writing, root)
    reseal_test_cell(root, deepcopy(observed))
    with pytest.raises(AssertionError):
        study.load_written(root / "writing", cfg)


def positive_rows(loop=.75, fixed=.5):
    return [{"tissue": t, "passes": True, "gates": {"checked": True},
             "arms": {a: {"accuracy": 1. if a == "parent" else loop if a == "loop" else fixed if a == "fixed" else .25}
                      for a in study.readout.ARMS}} for t in study.TISSUES]


def calibrations(failed=None):
    return [{"tissue": t, "passes": True, "gates": {"checked": True},
             **{name: {"tissue": t, "passes": True, "gates": {"checked": True}, "positive_accuracy": .25 if name == failed else 1.}
                for name in ("legacy", "readout")}} for t in study.TISSUES]


@pytest.mark.parametrize("loop,fixed,label", (
    (.75, .5, "FRESH_FEEDBACK_RELIABILITY_REPLICATED"), (.75, .75, "FRESH_WRITING_RELIABILITY_REPLICATED"),
    (.25, .75, "FIXED_READER_WRITING_REPLICATION_ONLY"), (.25, .25, "NO_QUALIFIED_FRESH_WRITING_BENEFIT")))
def test_new_panel_endpoints_are_independently_recomputed(loop, fixed, label, checker):
    rows = positive_rows(loop, fixed)
    result = study.classify(rows)
    assert result["label"] == label
    checker.common.close(result, checker.adjudicate([{"tissue": r["tissue"], "readout": r} for r in rows]))
    assert all(c["seed"] in study.SEEDS and type(c["supported"]) is bool for c in result["co_primary"].values())


def test_no_reuse_relaxed_consistency_or_legacy_parent_gate():
    rows = positive_rows()
    for row in rows[-5:]:
        row["arms"]["damaged"]["accuracy"] = .75
    c = study.classify(rows)["co_primary"]["loop_vs_damaged"]
    assert c["interval"][0] > 0 and c["positive_tissues"] == 11 and c["supported"] is False
    rows[0]["arms"]["parent"]["accuracy"] = .25
    assert study.classify(rows)["label"] == "PARENT_THETA_NOT_READABLE"
    assert study.classify(rows[:-1])["label"] == "INVALID_STRUCTURAL_FAILURE"
    for row, old in zip(rows, study.readout.TISSUES):
        row["tissue"] = old
    assert study.classify(rows)["label"] == "INVALID_STRUCTURAL_FAILURE"
    rows = positive_rows()
    rows[0]["gates"]["checked"] = "True"
    assert study.classify(rows)["label"] == "INVALID_STRUCTURAL_FAILURE"


def test_two_instrument_gates_and_strict_json(cell, tmp_path):
    assert study.calibrated(calibrations()) is True
    for failed in ("legacy", "readout"):
        assert study.calibrated(calibrations(failed)) is False
    assert study.calibrated(calibrations()[:-1]) is False
    study.strict_json(tmp_path / "good.json", {"writing": cell[3], "readout": cell[4], "calibration": cell[5]}, tmp_path)
    for value in (np.bool_(True), np.int64(1), float("nan")):
        with pytest.raises((TypeError, ValueError)):
            study.strict_json(tmp_path / "bad.json", {"bad": value}, tmp_path)
        assert not (tmp_path / "bad.json").exists()


def test_fresh_tissue_reservation_checks_nested_manifests_and_output_dirs(tmp_path):
    assert study.fresh_panel(tmp_path)["passes"] is True
    own = tmp_path / "runs" / study.RUN_ID / "MANIFEST.json"
    study.strict_json(own, {"tissues": list(study.TISSUES)}, tmp_path)
    assert study.fresh_panel(tmp_path)["passes"] is True
    other = tmp_path / "runs" / "other_attempt" / "MANIFEST.json"
    study.strict_json(other, {"nested": {"tissues": [30024]}}, tmp_path)
    with pytest.raises(RuntimeError, match="reservation"):
        study.fresh_panel(tmp_path)
    study.strict_json(other, {"tissues": [30023]}, tmp_path)
    (tmp_path / "outputs" / "old_attempt" / "tissue_30039").mkdir(parents=True)
    with pytest.raises(RuntimeError, match="reservation"):
        study.fresh_panel(tmp_path)


@pytest.mark.parametrize("failed", (None, "legacy", "readout"))
def test_terminal_publication_and_all_calibrations_before_any_parent(failed, tmp_path, monkeypatch, capsys):
    run = tmp_path / "runs" / study.RUN_ID
    run.mkdir(parents=True)
    qualified = failed is None
    monkeypatch.setattr(study, "verify_prepared", lambda root: {"benchmark": {"must_detach": False}, "input_sha256": {"mock": "hash"}})
    monkeypatch.setattr(study.source, "runtime", lambda: {"passes": True})
    monkeypatch.setattr(study.source, "disk_preflight", lambda root: {"passes": True})
    monkeypatch.setattr(study.source.base, "verify_hashes", lambda hashes: True)
    monkeypatch.setattr(study.readout, "manifest_hashes", lambda path: dict.fromkeys(range(738 if qualified else 98), "hash"))
    rows = {r["tissue"]: r for r in positive_rows()}
    cals = {r["tissue"]: r for r in calibrations(failed)}
    calls = []
    class Pool:
        def __init__(self, **kwargs):
            assert kwargs["max_workers"] == 4
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False
        def submit(self, fn, index, root_text, stage):
            if stage == "writing":
                assert calls.count("calibration") == 16 and qualified
            if stage == "readout":
                assert calls.count("writing") == 16
            calls.append(stage)
            future = Future()
            future.set_result(cals[index] if stage == "calibration" else rows[index])
            return future
    monkeypatch.setattr(study, "ProcessPoolExecutor", Pool)
    assert study.run_study(tmp_path) == 0
    status = json.loads((run / "STATUS.json").read_text())
    assert json.loads(capsys.readouterr().out) == status
    assert status["status"] == "COMPLETE" and status["calibration_qualified"] is qualified
    assert status["completed_writing_tissues"] == status["completed_readout_tissues"] == (16 if qualified else 0)
    assert len(calls) == (48 if qualified else 16)
    assert (run / "COMPLETE").is_file() and not (run / "FAILED").exists()


def test_long_runs_require_detach_and_never_poll(tmp_path, monkeypatch, checker):
    for module, runner, verifier in ((study, study.run_study, "verify_prepared"), (checker, checker.run_audit, "verify")):
        run = tmp_path / "runs" / module.RUN_ID
        run.mkdir(parents=True)
        monkeypatch.setattr(module, verifier, lambda root: {"benchmark": {"must_detach": True, "projected_seconds": 901}})
        with pytest.raises(RuntimeError, match="detached"):
            runner(tmp_path)
        calls = []
        def spawn(command, **kwargs):
            calls.append((command, kwargs))
            return SimpleNamespace(pid=400101)  # No poll/wait methods.
        monkeypatch.setattr(module.subprocess, "Popen", spawn)
        result = module.detach(tmp_path)
        assert result["polling_owner"] == "user" and calls[0][1]["start_new_session"]
        assert calls[0][1]["stdin"] == module.subprocess.DEVNULL
        with pytest.raises(FileExistsError):
            module.detach(tmp_path)


def test_prepared_inputs_draw_count_and_tissue_reservation_are_immutable(tmp_path, monkeypatch):
    run = tmp_path / "runs" / study.RUN_ID
    run.mkdir(parents=True)
    source_file = tmp_path / "source.txt"
    study.atomic_text(source_file, "frozen", tmp_path)
    study.strict_json(study.benchmark_path(tmp_path), {"passes": True}, tmp_path)
    monkeypatch.setattr(study, "input_paths", lambda root: [source_file])
    hashes = {str(p): study.sha256_file(p) for p in (source_file, study.benchmark_path(tmp_path))}
    manifest = study.contract() | {"input_sha256": hashes, "hash_contract": study.canonical_digest(hashes)}
    study.strict_json(run / "MANIFEST.json", manifest, tmp_path)
    study.strict_json(run / "STATUS.json", {"status": "PREPARED"}, tmp_path)
    assert study.verify_prepared(tmp_path)["workers"] == 4
    bad = deepcopy(manifest)
    bad["readout_config"]["draws"] = 17
    study.strict_json(run / "MANIFEST.json", bad, tmp_path)
    with pytest.raises(RuntimeError, match="contract changed"):
        study.verify_prepared(tmp_path)
    study.strict_json(run / "MANIFEST.json", manifest, tmp_path)
    study.atomic_text(source_file, "changed", tmp_path)
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
    study.strict_json(tmp_path / "runs" / study.SOURCE_ID / "STATUS.json", {"status": "FAILED"}, tmp_path)
    with pytest.raises(AssertionError):
        study.source_info(tmp_path)


@pytest.mark.parametrize("failed", (None, "legacy", "readout"))
def test_independent_audit_publishes_success_and_unqualified_paths(failed, tmp_path, monkeypatch, checker):
    run = tmp_path / "runs" / checker.RUN_ID
    run.mkdir(parents=True)
    qualified = failed is None
    rows = positive_rows() if qualified else []
    source = {"calibrations": calibrations(failed), "writing": rows, "readout": rows,
              "calibration_qualified": qualified, "classification": study.classify(rows) if qualified else {"label": "INSTRUMENT_NOT_QUALIFIED"}}
    monkeypatch.setattr(checker, "verify", lambda root: {"benchmark": {"must_detach": False}, "input_sha256": {"mock": "hash"}})
    monkeypatch.setattr(checker, "verify_hashes", lambda hashes: True)
    monkeypatch.setattr(checker, "runtime", lambda root: [0, 1, 2, 3])
    monkeypatch.setattr(checker, "source_info", lambda root: (source, [899, 738 if qualified else 98]))
    monkeypatch.setattr(checker, "check_calibration", lambda directory, saved: {n: saved[n]["positive_accuracy"] for n in ("legacy", "readout")})
    monkeypatch.setattr(checker, "check_tissue", lambda directory, written, observed: {"tissue": written["tissue"], "writing": written, "readout": observed})
    study.atomic_text(tmp_path / "outputs" / checker.RUN_ID / "input_hashes.sha256", "mock input evidence\n", tmp_path)
    assert checker.run_audit(tmp_path) == 0
    status = json.loads((run / "STATUS.json").read_text())
    result = json.loads((tmp_path / "outputs" / checker.RUN_ID / "rescore.json").read_text())
    assert status["status"] == "COMPLETE" and status["new_simulations"] == 0
    assert result["recovery_batches_checked"] == (160 if qualified else 0)
    assert result["scientific_readout_batches_checked"] == (96 if qualified else 0)
    assert result["calibration_batches_checked"] == 64
    assert result["batch_writer_recurrences_checked"] == (160000 if qualified else 0)
    assert (run / "COMPLETE").is_file() and not (run / "FAILED").exists()
