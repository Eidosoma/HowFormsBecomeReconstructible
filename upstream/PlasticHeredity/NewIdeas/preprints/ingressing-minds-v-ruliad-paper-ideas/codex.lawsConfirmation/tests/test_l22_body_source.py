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

from laws_confirmation import l22_body_source as study


@pytest.fixture(scope="module")
def checker():
    path = Path(__file__).resolve().parents[1] / "scripts/audit_l22_body_source_outputs.py"
    spec = importlib.util.spec_from_file_location("body_source_tests_checker", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("tied", (False, True))
def test_rank_transfer_preserves_exact_values_fill_and_self_identity(tied, checker):
    rng = np.random.default_rng(410110)
    kept = rng.standard_normal((8, 16, 16))
    if tied:
        kept = kept.round(0)
    fresh = np.zeros_like(kept, dtype=bool)
    fresh[:, 8:] = True
    old = kept.copy()
    result = study.donor_ranked(kept, fresh, 2)
    independent = checker.rank_body(kept, fresh, 2)
    for key in result:
        np.testing.assert_array_equal(result[key], independent[key])
    identity = study.donor_ranked(kept, fresh, 2, np.arange(8))
    np.testing.assert_array_equal(identity["donor_V"], kept)
    np.testing.assert_array_equal(kept, old)
    for i in range(8):
        np.testing.assert_array_equal(np.sort(result["donor_V"][i][~fresh[i]]), np.sort(kept[i][~fresh[i]]))
        np.testing.assert_array_equal(result["donor_V"][i][fresh[i]], kept[i][fresh[i]])
    assert result["donor_indices"].tolist() == [2, 3, 4, 5, 6, 7, 0, 1]


def test_rank_rejects_invalid_masks_donors_and_nonfinite():
    kept = np.arange(1024, dtype=np.float64).reshape(4, 16, 16)
    fresh = np.zeros_like(kept, dtype=bool)
    fresh[:, 8:] = True
    with pytest.raises(AssertionError):
        study.donor_ranked(kept, fresh, 1, [0, 0, 1, 2])
    bad = fresh.copy()
    bad[1, 0, 0] = True
    with pytest.raises(AssertionError):
        study.donor_ranked(kept, bad, 1)
    kept[0, 0, 0] = np.nan
    with pytest.raises(AssertionError):
        study.donor_ranked(kept, fresh, 1)


def test_donor_scoring_is_specific_not_just_loss_of_own_message(checker):
    cfg = study.readout.Config(parents=1, draws=2)
    labels = np.repeat(np.arange(4), 2)
    for shift, donor in ((0, 0.), (1, 1.), (2, 0.)):
        probabilities = np.eye(4)[(labels + shift) % 4]
        raw = {"probabilities": probabilities, "correctness": probabilities[np.arange(8), labels].reshape(4, 2)}
        value = study.donor_metrics(raw, cfg)
        assert value["donor_accuracy"] == donor
        checker.common.close(value, checker.donor_scores(raw, asdict(cfg)))


def build_cell(root, cfg, rcfg):
    ctx = study.source.context(400111, cfg)
    calibration, arrays = study.prior.calibration(ctx, rcfg)
    for name, raw in arrays.items():
        study.save_arrays(root / name, raw, root, "calibration_")
        study.strict_json(root / name / "calibration.json", calibration["legacy" if name == "writing" else "readout"], root)
    written, raw, extras = study.experiment_writing(ctx)
    study.save_writing(root, written, raw, extras, root)
    observed, raw = study.read_written(ctx, root, rcfg)
    study.save_arrays(root / "readout", raw, root)
    study.strict_json(root / "readout/experiment.json", observed, root)
    return root, cfg, rcfg, json.loads(json.dumps(written)), json.loads(json.dumps(observed)), calibration


@pytest.fixture(scope="module")
def cell(tmp_path_factory):
    root = tmp_path_factory.mktemp("body-source-cell")
    cfg = study.source.Config(replicates=1, settle=4, imprint=8, sweeps=32, times=(0, 1, 8, 16, 32))
    rcfg = study.readout.Config(parents=1, draws=2, sweeps=32, times=(0, 1, 32))
    return build_cell(root, cfg, rcfg)


def test_whole_current_cell_and_independent_data_counts(cell, checker):
    root, cfg, rcfg, written, observed, cal = cell
    checked = checker.check_tissue(root, written, observed, json.loads(json.dumps(asdict(cfg))), json.loads(json.dumps(asdict(rcfg))))
    checker.check_calibration(root, cal, json.loads(json.dumps(asdict(cfg))), json.loads(json.dumps(asdict(rcfg))))
    assert set(checked["writing"]["intervention"]["recovery"]) == set(study.EXTRA)
    assert len(checked["readout"]["arms"]) == 13 and len(checked["readout"]["legacy"]) == 11
    assert len(list(root.rglob("*.*"))) == 71
    assert len(list((root / "writing").iterdir())) == 31
    assert len(list((root / "intervention").iterdir())) == 11
    assert len(list((root / "readout").iterdir())) == 29
    packets = study.load_written(root, cfg, 400111)
    assert len(packets) == 11 and all(len(p) == 8192 for p in packets.values())
    assert packets["donor_off"] == packets["scrambled_off"] == packets["kept_off"] == packets["damaged"]


def test_full_thousand_update_cell(tmp_path, checker):
    cfg = study.source.Config(replicates=1, settle=4, imprint=8, sweeps=1000, times=(0, 1, 1000))
    rcfg = study.readout.Config(parents=1, draws=2, sweeps=1000, times=(0, 1, 1000))
    root, _, _, written, observed, _ = build_cell(tmp_path, cfg, rcfg)
    checker.check_tissue(root, written, observed, json.loads(json.dumps(asdict(cfg))), json.loads(json.dumps(asdict(rcfg))))


def reseal(root, observed):
    for folder, name in (("writing", "writing_hashes.sha256"), ("intervention", "intervention_hashes.sha256")):
        directory = root / folder
        files = [p for p in directory.glob("*.npz") if not p.name.startswith("calibration_")] + [directory / "experiment.json"]
        study.write_hash_manifest(files, directory / name, root)
    observed["writing_manifest_sha256"] = study.writing_manifests(root)
    study.strict_json(root / "readout/experiment.json", observed, root)


@pytest.mark.parametrize("kind", ("rank_body", "rank_order", "rank_index", "writer_trace", "fixed_reader", "probe_birth", "packet", "theta", "scores", "donor_score", "origin"))
def test_rehashed_tampering_rejected(kind, cell, checker, tmp_path):
    original, cfg, rcfg, written, observed, _ = cell
    root = tmp_path / "cell"
    shutil.copytree(original, root)
    saved = deepcopy(observed)
    if kind == "origin":
        saved["packet_origin"] = "retained_old_packet"
    elif kind == "donor_score":
        saved["arms"]["donor_loop"]["donor_accuracy"] += .1
    else:
        folder, filename, key = {
            "rank_body": ("intervention", "bodies", "donor_V"), "rank_order": ("intervention", "bodies", "donor_order"),
            "rank_index": ("intervention", "bodies", "donor_indices"), "writer_trace": ("intervention", "recovery_donor_loop", "theta_trace"),
            "fixed_reader": ("intervention", "recovery_donor_fixed", "fixed_reader"), "probe_birth": ("intervention", "probe_donor_loop", "s0_V"),
            "packet": ("readout", "packets", "donor_loop"), "theta": ("readout", "readout_donor_loop", "s1_theta"),
            "scores": ("readout", "readout_donor_loop", "scores"),
        }[kind]
        path = root / folder / f"{filename}.npz"
        raw = checker.common.arrays(path)
        raw[key].flat[0] += 1 if raw[key].dtype.kind in "iu" else .1
        study.source.base.atomic_npz(path, raw, root)
    reseal(root, saved)
    with pytest.raises(AssertionError):
        checker.check_tissue(root, written, saved, json.loads(json.dumps(asdict(cfg))), json.loads(json.dumps(asdict(rcfg))))


def test_loader_current_tissue_paths_and_packet_checks(cell, tmp_path):
    original, cfg, _, _, observed, _ = cell
    with pytest.raises(AssertionError):
        study.load_written(original, cfg, 400112)
    root = tmp_path / "rebased"
    shutil.copytree(original, root)
    with pytest.raises(AssertionError):
        study.load_written(root, cfg)
    extra = json.loads((root / "intervention/experiment.json").read_text())
    extra["probe_packet_hashes"]["donor_loop"] = "0" * 64
    study.strict_json(root / "intervention/experiment.json", extra, root)
    reseal(root, deepcopy(observed))
    with pytest.raises(AssertionError):
        study.load_written(root, cfg)


def positive_rows(useful=True, organized=True, donor=True):
    rows = []
    for tissue in study.TISSUES:
        arms = {a: {"accuracy": .25, "donor_accuracy": .25} for a in study.ARMS}
        arms["parent"]["accuracy"] = 1.
        arms["kept_loop"]["accuracy"] = .75
        arms["damaged"]["accuracy"] = .25 if useful else .75
        arms["scrambled_loop"]["accuracy"] = .5 if organized else .75
        arms["donor_loop"]["donor_accuracy"] = .5 if donor else .25
        rows.append({"tissue": tissue, "passes": True, "gates": {"checked": True}, "arms": arms})
    return rows


def calibrations(failed=None):
    return [{"tissue": t, "passes": True, "gates": {"checked": True},
             **{n: {"tissue": t, "passes": True, "gates": {"checked": True}, "positive_accuracy": .25 if n == failed else 1.}
                for n in ("legacy", "readout")}} for t in study.TISSUES]


@pytest.mark.parametrize("useful,organized,donor,label", (
    (True, True, True, "BODY_CONTENT_SPECIFIC_REPAIR_SUPPORTED"),
    (False, True, True, "BODY_CONTENT_REDIRECTION_WITHOUT_QUALIFIED_REPAIR"),
    (True, True, False, "BODY_ORGANIZATION_BENEFIT_ONLY"),
    (True, False, True, "DONOR_BODY_REDIRECTION_ONLY"),
    (True, False, False, "REPAIR_WITHOUT_QUALIFIED_BODY_SOURCE"),
    (False, False, False, "NO_QUALIFIED_BODY_SOURCE_EFFECT")))
def test_fixed_labels_and_independent_clustered_bootstrap(useful, organized, donor, label, checker):
    rows = positive_rows(useful, organized, donor)
    result = study.classify(rows)
    assert result["label"] == label
    checker.common.close(result, checker.adjudicate([{"tissue": r["tissue"], "readout": r} for r in rows]))
    assert all(c["seed"] in study.SEEDS and type(c["supported"]) is bool for c in result["co_primary"].values())


def test_no_relaxed_consistency_no_old_tissues_or_loss_only_donor_claim():
    rows = positive_rows()
    for row in rows[-5:]:
        row["arms"]["scrambled_loop"]["accuracy"] = .75
    c = study.classify(rows)["co_primary"]["body_organization"]
    assert c["interval"][0] > 0 and c["positive_tissues"] == 11 and c["supported"] is False
    rows = positive_rows(donor=False)
    for row in rows:
        row["arms"]["donor_loop"]["accuracy"] = 0.
    assert study.classify(rows)["co_primary"]["donor_redirection"]["supported"] is False
    rows[0]["arms"]["parent"]["accuracy"] = .25
    assert study.classify(rows)["label"] == "PARENT_THETA_NOT_READABLE"
    assert study.classify(rows[:-1])["label"] == "INVALID_STRUCTURAL_FAILURE"
    rows = positive_rows()
    rows[0]["tissue"] = 30024
    assert study.classify(rows)["label"] == "INVALID_STRUCTURAL_FAILURE"
    rows = positive_rows()
    rows[0]["gates"]["checked"] = "True"
    assert study.classify(rows)["label"] == "INVALID_STRUCTURAL_FAILURE"


def test_registry_and_frozen_native_contract(checker):
    c = study.contract()
    assert study.TISSUES == tuple(range(30040, 30056)) and not set(study.TISSUES) & set(study.prior.TISSUES)
    assert c["total_lives"] == sum(c[k] for k in ("parent_lives", "recovery_lives", "legacy_diagnostic_readouts", "legacy_calibration_lives",
        "writing_integrity_lives", "scientific_readout_lives", "readout_calibration_lives", "readout_replay_lives", "legacy_wrapper_replay_lives")) == 87040
    assert c["qualified_output_hashes"] == 16 * 71 + 2 == 1138 and c["unqualified_output_hashes"] == 98
    assert len(study.ARMS) == 13 and len(study.EXTRA) == 4 and len(study.PACKETS) == 11
    assert c["workers"] == 4 and c["minimum_positive_tissues"] == 12 and c["retained_scientific_packets_used"] == 0
    checker.common.close(json.loads(json.dumps(c["config"])), checker.CFG)
    checker.common.close(json.loads(json.dumps(c["readout_config"])), checker.RCFG)
    assert study.CONFIG == study.prior.CONFIG and study.READOUT_CONFIG.draws == 16
    assert study.prior.TISSUES == tuple(range(30024, 30040))


def test_calibrations_and_strict_json(tmp_path):
    assert study.calibrated(calibrations())
    for failed in ("legacy", "readout"):
        assert study.calibrated(calibrations(failed)) is False
    rows = calibrations()
    rows[0]["legacy"]["tissue"] = 0
    assert study.calibrated(rows) is False
    for value in (np.bool_(True), np.int64(1), float("nan")):
        with pytest.raises((TypeError, ValueError)):
            study.strict_json(tmp_path / "bad.json", {"bad": value}, tmp_path)
        assert not (tmp_path / "bad.json").exists()


def test_reservation_and_immutable_prepared_contract(tmp_path, monkeypatch):
    assert study.fresh_panel(tmp_path)["passes"]
    conflict = tmp_path / "runs/old/MANIFEST.json"
    study.strict_json(conflict, {"nested": {"tissue": 30040}}, tmp_path)
    with pytest.raises(RuntimeError, match="reservation"):
        study.fresh_panel(tmp_path)
    study.strict_json(conflict, {"tissues": [30039]}, tmp_path)
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
    bad["donor_offset"] = 2
    study.strict_json(run / "MANIFEST.json", bad, tmp_path)
    with pytest.raises(RuntimeError, match="contract changed"):
        study.verify_prepared(tmp_path)
    study.strict_json(run / "MANIFEST.json", manifest, tmp_path)
    study.atomic_text(source_file, "changed", tmp_path)
    with pytest.raises(RuntimeError, match="contract changed"):
        study.verify_prepared(tmp_path)
    with pytest.raises(FileExistsError):
        study.prepare(tmp_path)


@pytest.mark.parametrize("failed", (None, "legacy", "readout"))
def test_calibration_stage_order_and_terminal_publication(failed, tmp_path, monkeypatch, capsys):
    run = tmp_path / "runs" / study.RUN_ID
    run.mkdir(parents=True)
    qualified = failed is None
    evidence = tmp_path / "frozen_input.txt"
    study.atomic_text(evidence, "publication fixture", tmp_path)
    hashes = {str(evidence): study.sha256_file(evidence)}
    monkeypatch.setattr(study, "verify_prepared", lambda root: {"benchmark": {"must_detach": False}, "input_sha256": hashes})
    monkeypatch.setattr(study.source, "runtime", lambda: {"passes": True})
    monkeypatch.setattr(study, "disk_preflight", lambda root: {"passes": True})
    monkeypatch.setattr(study.readout, "manifest_hashes", lambda path: dict.fromkeys(range(1138 if qualified else 98), "hash"))
    rows, cals = {r["tissue"]: r for r in positive_rows()}, {r["tissue"]: r for r in calibrations(failed)}
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


def test_detach_required_and_launch_never_polls(tmp_path, monkeypatch, checker):
    for module, runner, verifier in ((study, study.run_study, "verify_prepared"), (checker, checker.run_audit, "verify")):
        run = tmp_path / "runs" / module.RUN_ID
        run.mkdir(parents=True)
        monkeypatch.setattr(module, verifier, lambda root: {"benchmark": {"must_detach": True, "projected_seconds": 901}})
        with pytest.raises(RuntimeError, match="detached"):
            runner(tmp_path)
        calls = []
        def spawn(command, **kwargs):
            calls.append((command, kwargs))
            return SimpleNamespace(pid=410111)  # Deliberately no poll/wait method.
        monkeypatch.setattr(module.subprocess, "Popen", spawn)
        record = module.detach(tmp_path)
        assert record["polling_owner"] == "user"
        assert calls[0][1]["start_new_session"] and calls[0][1]["stdin"] == module.subprocess.DEVNULL
        with pytest.raises(FileExistsError):
            module.detach(tmp_path)


def test_runtime_failure_is_preserved_and_failed_source_refused(tmp_path, monkeypatch, checker):
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
def test_independent_audit_complete_and_instrument_unqualified(failed, tmp_path, monkeypatch, checker):
    run = tmp_path / "runs" / checker.RUN_ID
    run.mkdir(parents=True)
    qualified = failed is None
    rows = positive_rows() if qualified else []
    result = {"calibrations": calibrations(failed), "writing": rows, "readout": rows,
              "calibration_qualified": qualified, "classification": study.classify(rows) if qualified else {"label": "INSTRUMENT_NOT_QUALIFIED"}}
    evidence = tmp_path / "frozen_input.txt"
    study.atomic_text(evidence, "independent publication fixture", tmp_path)
    hashes = {str(evidence): study.sha256_file(evidence)}
    monkeypatch.setattr(checker, "verify", lambda root: {"benchmark": {"must_detach": False}, "input_sha256": hashes})
    monkeypatch.setattr(checker, "runtime", lambda root: [0, 1, 2, 3])
    monkeypatch.setattr(checker, "source_info", lambda root: (result, [1655, 1138 if qualified else 98]))
    monkeypatch.setattr(checker, "check_calibration", lambda directory, saved: {n: saved[n]["positive_accuracy"] for n in ("legacy", "readout")})
    monkeypatch.setattr(checker, "check_tissue", lambda directory, written, observed: {"tissue": written["tissue"], "writing": written, "readout": observed})
    study.write_hash_manifest([evidence], tmp_path / "outputs" / checker.RUN_ID / "input_hashes.sha256", tmp_path)
    assert checker.run_audit(tmp_path) == 0
    status = json.loads((run / "STATUS.json").read_text())
    checked = json.loads((tmp_path / "outputs" / checker.RUN_ID / "rescore.json").read_text())
    assert status["status"] == "COMPLETE" and status["new_simulations"] == 0
    assert checked["recovery_batches_checked"] == (224 if qualified else 0)
    assert checked["legacy_diagnostic_batches_checked"] == (272 if qualified else 0)
    assert checked["scientific_readout_batches_checked"] == (208 if qualified else 0)
    assert checked["legacy_wrapper_batches_checked"] == (176 if qualified else 0)
    assert checked["calibration_batches_checked"] == 64
    assert checked["batch_writer_recurrences_checked"] == (224000 if qualified else 0)
    assert checked["rank_transfers_checked"] == (256 if qualified else 0)
    assert (run / "COMPLETE").is_file() and not (run / "FAILED").exists()
