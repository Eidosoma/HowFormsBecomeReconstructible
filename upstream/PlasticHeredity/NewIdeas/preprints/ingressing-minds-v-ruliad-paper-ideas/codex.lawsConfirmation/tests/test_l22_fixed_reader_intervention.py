from copy import deepcopy
from dataclasses import asdict, replace
import json
from pathlib import Path
import shutil
from types import SimpleNamespace

import numpy as np
import pytest

from laws_confirmation import l22_fixed_reader_intervention as study


@pytest.fixture(scope="module")
def check():
    return study.checker()


def test_frozen_design_separates_reading_and_writing(check):
    contract = study.contract()
    assert study.TISSUES == check.TISSUES == tuple(range(30040, 30056))
    assert study.MAIN == check.MAIN and study.ARMS == check.ARMS and len(study.ANCHORS) == 4
    assert contract["new_parents"] == contract["functional_readouts"] == contract["law_verdict_changes"] == 0
    assert contract["workers"] == 4 and contract["executed_recovery_cells"] == 128
    assert contract["focal_endpoint"] == [50, "V", "donor_accuracy"]
    for arm in study.ARMS:
        mode = study.mode(arm)
        assert mode.reader in ("native", "damaged") and mode.reference == "zero" and not mode.hold
        assert mode.write is (not arm.endswith("_off"))
    with pytest.raises(ValueError):
        study.mode("donor_live")


@pytest.fixture(scope="module")
def disposable(tmp_path_factory, check):
    """Real full-length dynamics on an explicitly non-scientific tissue."""
    root = tmp_path_factory.mktemp("fixed-reader-disposable")
    tissue = 402076
    ctx = study.source.context(tissue, study.CONFIG)
    _, parent = study.source.prepare_parent(ctx)
    kept, scrambled, fresh, damaged = study.source.boundary(ctx, parent)
    boundary = dict(kept_V=kept["V"], scrambled_V=scrambled, fresh=fresh,
                    damaged_theta=damaged, native_theta=ctx["native"])
    ranked = study.bodies.donor_ranked(kept["V"], fresh, 4)
    original = root/"outputs"/study.SOURCE_ID/f"tissue_{tissue}"
    (original/"writing").mkdir(parents=True)
    (original/"intervention").mkdir()
    study.save_npz(original/"writing/parent.npz", parent, root)
    study.save_npz(original/"writing/boundary.npz", boundary, root)
    study.save_npz(original/"intervention/bodies.npz", ranked, root)
    initial = study.initial_states(boundary, ranked)
    for arm, (folder, old) in study.ANCHORS.items():
        result = study.writing.recover(ctx, initial[arm], study.mode(arm), parent, fresh)
        study.save_npz(original/folder/f"recovery_{old}.npz", result["raw"], root)
    off = study.writing.recover(ctx, initial["kept_native"], replace(study.mode("kept_native"), write=False), parent, fresh)
    study.save_npz(original/"writing/recovery_body_writer_off.npz", off["raw"], root)
    metadata = dict(tissue=tissue, passes=True, gates={"fixture": True}, config=asdict(study.CONFIG),
                    tissue_config=asdict(ctx["tissue"]), source_parent_sha256=study.source.base.state_digest(parent),
                    source_native_sha256=study.source.base.array_digest(ctx["native"]), recovery_rng_final=off["rng_final"])
    for folder in ("writing", "intervention"):
        study.strict_json(original/folder/"experiment.json", metadata, root)
    # Only this unit fixture can use its disposable index; production defaults stay literal.
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(check, "TISSUES", (tissue,))
        mp.setattr(study, "checker", lambda: check)
        data, saved, checked = study.execute_cell(root, tissue, root/"result")
    return root, original, tissue, data, saved, checked


def test_full_disposable_cell_publication_and_independent_verification(disposable, check):
    root, original, tissue, data, saved, checked = disposable
    assert checked["replay_anchors"] == 4 and checked["fixed_off_pairs"] == 3
    assert checked["recorded_batch_steps"] == 8000 and len(list((root/"result").iterdir())) == 10
    assert check.check_pool([data]*16, study.pooled([data]*16))
    with pytest.raises(ValueError):
        study.pooled([data]*15)
    for arm in study.MAIN:
        other = study.checker().common.arrays(root/"result"/f"recovery_{arm}.npz")
        np.testing.assert_array_equal(other["s0_theta"], check.common.arrays(original/"writing/boundary.npz")["damaged_theta"])


@pytest.mark.parametrize("kind", ("reader", "initial_theta", "R_recurrence", "theta_scale", "theta_extra_axis", "native_off_ema", "anchor", "curve", "stratum", "summary", "rng"))
def test_saved_data_tampering_rejected(disposable, check, tmp_path, monkeypatch, kind):
    root, original, tissue, _, _, _ = disposable
    output = tmp_path/"cell"
    shutil.copytree(root/"result", output)
    monkeypatch.setattr(check, "TISSUES", (tissue,))
    if kind in ("summary", "rng"):
        path = output/"analysis.json"
        saved = json.loads(path.read_text())
        if kind == "summary":
            saved["arms"]["donor_native"]["50"]["V"]["mean"]["donor_accuracy"] += .1
        else:
            saved["recovery_rng_final"]["donor_native"] = "0"*64
        study.strict_json(path, saved, tmp_path)
    else:
        arm, key = {
            "reader": ("donor_native", "fixed_reader"), "initial_theta": ("donor_native", "s0_theta"),
            "R_recurrence": ("donor_native", "reference_trace"), "theta_scale": ("donor_native", "projection_scale"),
            "theta_extra_axis": ("donor_native", "theta_trace"), "native_off_ema": ("donor_native_off", "s50_ema"),
            "anchor": ("kept_damaged", "s50_ema"), "curve": (None, "curves"), "stratum": (None, "strata")}[kind]
        path = output/(f"recovery_{arm}.npz" if arm else "analysis.npz")
        raw = check.common.arrays(path)
        if kind == "theta_extra_axis":
            raw[key][2, 0, 5] += .1
        else:
            raw[key].flat[0] += .1
        study.source.base.atomic_npz(path, raw, tmp_path)
    with pytest.raises(AssertionError):
        check.check_cell(original, output, tissue)


def test_common_reader_shift_is_not_donor_specific(check):
    data = dict(curves=np.zeros((6, 1001, 3, 5)), strata=np.zeros((6, 6, 4, 3, 5)))
    for arm in (1, 3, 5):
        data["curves"][arm, :, 0, 4] = .2
        data["strata"][arm, :, :, 0, 4] = .2
    summary = study.pooled([data]*16)
    contrast = summary["contrasts"]
    assert contrast["donor_native_minus_damaged"]["mean"][2][0][4] == pytest.approx(.2)
    assert contrast["donor_specific_reader_interaction"]["mean"][2][0][4] == 0.
    assert contrast["donor_specific_reader_interaction"]["tied"][2][0][4] == 16
    assert check.check_pool([data]*16, summary)
    data["curves"][5, :, 0, 4] += .1
    data["strata"][5, :, :, 0, 4] += .1
    summary = study.pooled([data]*16)
    assert summary["contrasts"]["donor_specific_reader_interaction"]["mean"][2][0][4] == pytest.approx(.1)
    assert check.check_pool([data]*16, summary)
    summary["contrasts"]["donor_specific_reader_interaction"]["message_mean"][2][0][0][4] += .1
    with pytest.raises(AssertionError):
        check.check_pool([data]*16, summary)


def prepared(root, monkeypatch, detached=False):
    path = root/"fixture.txt"
    study.atomic_text(path, "frozen fixture", root)
    monkeypatch.setattr(study, "input_paths", lambda _: [path])
    monkeypatch.setattr(study, "preflight", lambda _: [0, 1, 2, 3])
    seconds = 30. if detached else 2.
    timing = dict(run_id=study.RUN_ID, passes=True, must_detach=detached, tissue_seconds=seconds,
                  projected_seconds=seconds*24+90, input_sha256={str(path): study.sha256_file(path)})
    study.strict_json(study.timing_path(root), timing, root)
    study.prepare(root)
    return root/"runs"/study.RUN_ID


@pytest.mark.parametrize("key,value", (("workers", 5), ("new_parents", 16), ("focal_endpoint", [1000, "V", "donor_accuracy"]), ("law_verdict_changes", 1)))
def test_frozen_contract_tampering_rejected(tmp_path, monkeypatch, key, value):
    run = prepared(tmp_path, monkeypatch)
    record = json.loads((run/"MANIFEST.json").read_text())
    record[key] = value
    study.strict_json(run/"MANIFEST.json", record, tmp_path)
    with pytest.raises(AssertionError):
        study.verify(tmp_path)


def test_existing_output_and_changed_input_rejected(tmp_path, monkeypatch):
    prepared(tmp_path, monkeypatch)
    for fn in (study.prepare, study.benchmark):
        with pytest.raises(FileExistsError):
            fn(tmp_path)
    study.atomic_text(tmp_path/"fixture.txt", "changed", tmp_path)
    with pytest.raises(AssertionError):
        study.verify(tmp_path)


def test_detach_required_exclusive_and_never_polled(tmp_path, monkeypatch):
    run = prepared(tmp_path, monkeypatch, True)
    with pytest.raises(RuntimeError, match="detached"):
        study.run_intervention(tmp_path)
    assert not (run/"EXECUTION.lock").exists()
    calls = []
    def launch(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(pid=12345)
    monkeypatch.setattr(study.subprocess, "Popen", launch)
    record = study.detach(tmp_path)
    assert record["polling_owner"] == "user" and record["pid"] == 12345
    assert len(calls) == 1 and calls[0][1]["start_new_session"] is True
    assert "laws_confirmation.l22_fixed_reader_intervention" in calls[0][0] and "--run" in calls[0][0]
    with pytest.raises(FileExistsError):
        study.detach(tmp_path)


def test_failure_is_published_and_not_resumed(tmp_path, monkeypatch):
    run = prepared(tmp_path, monkeypatch)
    def fail(*args):
        raise ValueError("fixture failure")
    monkeypatch.setattr(study, "cells", fail)
    with pytest.raises(ValueError):
        study.run_intervention(tmp_path)
    assert (run/"FAILED").exists() and not (run/"COMPLETE").exists()
    with pytest.raises(AssertionError):
        study.run_intervention(tmp_path)


def test_successful_publication_and_output_hashes(disposable, tmp_path, monkeypatch, check):
    _, _, _, data, saved, checked = disposable
    run = prepared(tmp_path, monkeypatch)
    def fake_cells(root, output):
        for tissue in reversed(study.TISSUES):
            directory = output/f"tissue_{tissue}"
            directory.mkdir()
            for name in study.ARMS:
                study.save_npz(directory/f"recovery_{name}.npz", {"fixture": np.zeros(1)}, root)
            study.save_npz(directory/"analysis.npz", data, root)
            study.strict_json(directory/"analysis.json", saved | {"tissue": tissue}, root)
            yield tissue, (data, saved | {"tissue": tissue}, checked | {"tissue": tissue})
    monkeypatch.setattr(study, "cells", fake_cells)
    assert study.run_intervention(tmp_path) == 0
    assert (run/"COMPLETE").is_file() and not (run/"FAILED").exists()
    output = tmp_path/"outputs"/study.RUN_ID
    assert check.common.manifest_check(output/"output_hashes.sha256") == 163
    result = json.loads((output/"analysis.json").read_text())
    assert result["verified_saved_analysis"] is True and result["executed_recovery_cells"] == 128
    with pytest.raises(AssertionError):
        study.run_intervention(tmp_path)


@pytest.mark.parametrize("bad", (float("nan"), np.bool_(True)))
def test_strict_json_rejects_nonfinite_or_numpy_bool(tmp_path, bad):
    path = tmp_path/"bad.json"
    with pytest.raises((ValueError, TypeError)):
        study.strict_json(path, {"value": bad}, tmp_path)
    assert not path.exists()
