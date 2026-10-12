from copy import deepcopy
from dataclasses import asdict
import json
import shutil
from types import SimpleNamespace

import numpy as np
import pytest

from laws_confirmation import l22_residual_record_readout as study


@pytest.fixture(scope="module")
def check():
    return study.checker()


def build_fixture(root, cfg, check):
    tissue = 402077
    ctx = study.readout.context(tissue, cfg)
    synthetic = study.readout.synthetic_packets(ctx, cfg)
    packets = dict(donor_native=synthetic["loop"], scrambled_native=synthetic["fixed"],
                   donor_damaged=synthetic["fixed"], scrambled_damaged=synthetic["damaged"],
                   parent=synthetic["parent"], damaged=synthetic["damaged"])
    written = root/"outputs"/study.SOURCE_ID/f"tissue_{tissue}"
    ancestor = root/"outputs"/study.ANCESTOR_ID/f"tissue_{tissue}"
    written.mkdir(parents=True)
    (ancestor/"writing").mkdir(parents=True)
    (ancestor/"readout").mkdir()
    metadata = dict(tissue=tissue, passes=True, config=asdict(study.prior.CONFIG), source_native_sha256=study.source.base.array_digest(ctx["native"]))
    study.strict_json(written/"analysis.json", metadata, root)
    study.strict_json(ancestor/"writing/experiment.json", metadata, root)
    for a, packet in packets.items():
        value = np.frombuffer(packet, dtype=np.float64).reshape(16,16,16)
        path, key = ((written/f"recovery_{a}.npz", "s1000_theta") if a in study.MAIN else
                     (ancestor/"writing/parent.npz", "theta") if a == "parent" else (ancestor/"writing/boundary.npz", "damaged_theta"))
        study.save_npz(path, {key: value}, root)
    for arm, old in study.ANCHORS.items():
        result = study.readout.assay(ctx, packets[arm], cfg)
        study.save_npz(ancestor/"readout"/f"readout_{old}.npz", result["raw"], root)
    study.strict_json(ancestor/"readout/experiment.json", dict(tissue=tissue, passes=True, rng_final=result["rng_final"], birth_rng_final=result["birth_rng_final"]), root)
    cal, raw = study.readout.calibration(ctx, cfg)
    study.strict_json(ancestor/"readout/calibration.json", cal, root)
    for a, data in raw.items():
        study.save_npz(ancestor/"readout"/f"calibration_{a}.npz", data, root)
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(check, "TISSUES", (tissue,))
        mp.setattr(study, "checker", lambda: check)
        for stage in study.STAGES:
            saved, checked = study.execute_cell(root, tissue, stage, root/"result", cfg)
    return root, written, ancestor, cfg, saved, checked


@pytest.fixture(scope="module")
def example(tmp_path_factory, check):
    return build_fixture(tmp_path_factory.mktemp("residual-readout-fixture"), study.readout.Config(draws=2, sweeps=16, times=(0,1,16)), check)


def test_frozen_contract_counts_and_no_writing(check):
    c = study.contract()
    assert c["new_training_lives"] == c["new_writing_lives"] == c["law_verdict_changes"] == 0
    assert c["scored_readout_lives"]+c["replay_lives"]+c["calibration_lives"] == c["total_readout_lives"] == 53248
    assert c["workers"] == 4 and c["birth_stream_reused_for_matching"] is True
    assert study.TISSUES == check.TISSUES == tuple(range(30040,30056))
    assert study.ARMS == check.ARMS and study.ANCHORS == check.ANCHORS
    assert c["output_hashes"] == 211 and c["config"]["draws"] == 16


def test_saved_cell_and_full_thousand_step_path(example, tmp_path, check):
    root, written, ancestor, cfg, saved, checked = example
    assert len(list((root/"result").iterdir())) == 13
    assert checked["historical_readout_anchors"] == 4 and checked["packet_origins_checked"] == 6
    full = build_fixture(tmp_path, study.readout.Config(draws=2), check)
    assert full[-1]["scored_readout_lives"] == 256


def test_donor_observer_distinguishes_wrong_message_from_own_loss(check):
    cfg = study.readout.Config(draws=2)
    labels = np.repeat(np.arange(4), 8)
    for shift, expected in ((0,0.), (1,1.), (2,0.)):
        probabilities = np.eye(4)[(labels+shift) % 4]
        raw = dict(probabilities=probabilities, correctness=probabilities[np.arange(32),labels].reshape(16,2))
        extra = study.extra_metrics(raw,cfg)
        assert extra["donor_accuracy"] == expected
        check.common.close(extra, check.extra(raw,asdict(cfg)))
    tied = dict(probabilities=np.full((32,4),.25), correctness=np.full((16,2),.25))
    assert study.extra_metrics(tied,cfg)["donor_total_variance"] == 0.


@pytest.mark.parametrize("kind", ("packet", "birth", "theta", "R", "probability", "donor_score", "donor_variance", "paired", "wrong", "off", "rng", "origin", "anchor"))
def test_independent_saved_tamper_rejection(example, check, tmp_path, monkeypatch, kind):
    root, written, ancestor, cfg, _, _ = example
    output = tmp_path/"cell"
    shutil.copytree(root/"result", output)
    monkeypatch.setattr(check, "TISSUES", (402077,))
    if kind in ("donor_score", "donor_variance", "paired", "rng", "origin"):
        path = output/"experiment.json"
        value = json.loads(path.read_text())
        if kind == "rng":
            value["rng_final"] = "0"*64
        elif kind == "origin":
            value["packet_origin"] = "newly_trained"
        elif kind == "paired":
            value["paired"]["donor_minus_scrambled_native"]["donor"]["improved"] += .1
        else:
            value["arms"]["donor_native"]["donor_accuracy" if kind == "donor_score" else "donor_within_variance"] += .1
        study.strict_json(path, value, tmp_path)
    else:
        file,key = {"packet": ("packets", "donor_native"), "birth": ("readout_donor_native", "s0_ema"),
                    "theta": ("readout_donor_native", "s1_theta"), "R": ("readout_donor_native", "s1_R"),
                    "probability": ("readout_donor_native", "probabilities"), "wrong": ("readout_wrong", "s1_ema"),
                    "off": ("readout_reader_off", "s1_ema"), "anchor": ("readout_donor_damaged", "s1_ema")}[kind]
        path=output/f"{file}.npz"
        value=check.common.arrays(path)
        value[key].flat[0] += .1
        study.source.base.atomic_npz(path,value,tmp_path)
    with pytest.raises(AssertionError):
        check.check_cell(written,ancestor,output,402077,asdict(cfg))


def rows_from(example):
    saved = example[-2]
    return [deepcopy(saved) | {"tissue": t} for t in study.TISSUES]


def test_pool_and_common_reader_gain_is_not_specific(example,check):
    rows=rows_from(example)
    assert check.check_pool(rows,study.pooled(rows))
    for r in rows:
        for a in study.ARMS:
            value=.3 if a.endswith("native") else .2
            r["arms"][a].update(donor_accuracy=value,donor_message_accuracy=[value]*4)
    p=study.pooled(rows)
    assert p["contrasts"]["donor_native_minus_damaged"]["donor_accuracy"]["mean"] == pytest.approx(.1)
    assert p["contrasts"]["donor_specific_reader_interaction"]["donor_accuracy"]["mean"] == 0.
    assert check.check_pool(rows,p)
    p["contrasts"]["donor_specific_reader_interaction"]["donor_accuracy"]["positive"] = 16
    with pytest.raises(AssertionError):
        check.check_pool(rows,p)
    with pytest.raises(ValueError):
        study.pooled(rows[:-1])


def prepared(root,monkeypatch,detached=False):
    path=root/"fixture.txt"
    study.atomic_text(path,"frozen fixture",root)
    monkeypatch.setattr(study,"input_paths",lambda _: [path])
    monkeypatch.setattr(study,"preflight",lambda _: [0,1,2,3])
    seconds=30. if detached else 2.
    timing=dict(run_id=study.RUN_ID,passes=True,must_detach=detached,tissue_seconds=seconds,
                projected_seconds=seconds*24+90,input_sha256={str(path):study.sha256_file(path)})
    study.strict_json(study.timing_path(root),timing,root)
    study.prepare(root)
    return root/"runs"/study.RUN_ID


@pytest.mark.parametrize("key,value",(("workers",5),("new_writing_lives",16),("scored_readout_lives",65536),("direction_tolerance",.1)))
def test_contract_changes_rejected(tmp_path,monkeypatch,key,value):
    run=prepared(tmp_path,monkeypatch)
    value_json=json.loads((run/"MANIFEST.json").read_text())
    value_json[key]=value
    study.strict_json(run/"MANIFEST.json",value_json,tmp_path)
    with pytest.raises(AssertionError):
        study.verify(tmp_path)


def test_existing_or_changed_inputs_rejected(tmp_path,monkeypatch):
    prepared(tmp_path,monkeypatch)
    for fn in (study.prepare,study.benchmark):
        with pytest.raises(FileExistsError):
            fn(tmp_path)
    study.atomic_text(tmp_path/"fixture.txt","changed",tmp_path)
    with pytest.raises(AssertionError):
        study.verify(tmp_path)


def test_detach_exclusive_required_and_not_polled(tmp_path,monkeypatch):
    run=prepared(tmp_path,monkeypatch,True)
    with pytest.raises(RuntimeError,match="detached"):
        study.run_readout(tmp_path)
    assert not (run/"EXECUTION.lock").exists()
    calls=[]
    def launch(command,**kwargs):
        calls.append((command,kwargs))
        return SimpleNamespace(pid=12345)
    monkeypatch.setattr(study.subprocess,"Popen",launch)
    result=study.detach(tmp_path)
    assert result["polling_owner"]=="user" and result["pid"]==12345
    assert len(calls)==1 and calls[0][1]["start_new_session"] is True
    assert "laws_confirmation.l22_residual_record_readout" in calls[0][0]
    with pytest.raises(FileExistsError):
        study.detach(tmp_path)


def test_calibration_failure_prevents_all_scientific_readouts(tmp_path,monkeypatch):
    run=prepared(tmp_path,monkeypatch)
    stages=[]
    def bad_cells(root,output,stage):
        stages.append(stage)
        for t in study.TISSUES:
            yield t,(dict(tissue=t,passes=True,gates={"fixture":True},positive_accuracy=.25),dict(tissue=t,passes=True))
    monkeypatch.setattr(study,"cells",bad_cells)
    with pytest.raises(RuntimeError,match="calibration"):
        study.run_readout(tmp_path)
    assert stages==["calibration"] and (run/"FAILED").exists() and not (run/"COMPLETE").exists()
    with pytest.raises(AssertionError):
        study.run_readout(tmp_path)


def test_successful_two_stage_publication(example,check,tmp_path,monkeypatch):
    run=prepared(tmp_path,monkeypatch)
    rows={r["tissue"]:r for r in rows_from(example)}
    stages=[]
    def fake_cells(root,output,stage):
        stages.append(stage)
        for t in reversed(study.TISSUES):
            directory=output/f"tissue_{t}"
            if stage=="calibration":
                directory.mkdir()
                record=dict(tissue=t,passes=True,gates={"fixture":True},positive_accuracy=1.)
                study.strict_json(directory/"calibration.json",record,root)
                for name in ("positive","reader_off"):
                    study.save_npz(directory/f"calibration_{name}.npz",{"fixture":np.zeros(1)},root)
            else:
                record=rows[t]
                for name in (*[f"readout_{a}" for a in study.ARMS],"packets"):
                    study.save_npz(directory/f"{name}.npz",{"fixture":np.zeros(1)},root)
                study.strict_json(directory/"experiment.json",record,root)
            yield t,(record,dict(tissue=t,passes=True))
    monkeypatch.setattr(study,"cells",fake_cells)
    assert study.run_readout(tmp_path)==0 and stages==["calibration","readout"]
    assert (run/"COMPLETE").is_file() and not (run/"FAILED").exists()
    assert check.common.manifest_check(tmp_path/"outputs"/study.RUN_ID/"output_hashes.sha256")==211
    with pytest.raises(AssertionError):
        study.run_readout(tmp_path)


@pytest.mark.parametrize("bad",(float("nan"),np.bool_(True)))
def test_nonfinite_and_numpy_bool_not_published(tmp_path,bad):
    path=tmp_path/"invalid.json"
    with pytest.raises((TypeError,ValueError)):
        study.strict_json(path,{"value":bad},tmp_path)
    assert not path.exists()
