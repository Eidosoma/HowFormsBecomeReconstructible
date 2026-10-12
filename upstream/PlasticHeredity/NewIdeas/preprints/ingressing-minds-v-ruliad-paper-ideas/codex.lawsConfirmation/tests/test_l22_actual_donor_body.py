from copy import deepcopy
from dataclasses import asdict, replace
import json
from pathlib import Path
import shutil
from types import SimpleNamespace

import numpy as np
import pytest

from laws_confirmation import l22_actual_donor_body as study


@pytest.fixture(scope="module")
def check():
    return study.checker()


def build_fixture(root,cfg,rcfg,check):
    tissue = 402078
    ctx = study.source.context(tissue,cfg)
    _,parent = study.source.prepare_parent(ctx)
    kept,scrambled,fresh,damaged = study.source.boundary(ctx,parent)
    boundary = dict(kept_V=kept["V"],scrambled_V=scrambled,fresh=fresh,damaged_theta=damaged,native_theta=ctx["native"])
    ranked = study.fixed.bodies.donor_ranked(kept["V"],fresh,4)
    original = root/"outputs"/study.ANCESTOR_ID/f"tissue_{tissue}"
    writer = root/"outputs"/study.WRITING_ID/f"tissue_{tissue}"
    previous = root/"outputs"/study.SOURCE_ID/f"tissue_{tissue}"
    for path in (original/"writing",original/"intervention",original/"readout",writer,previous):
        path.mkdir(parents=True)
    study.save_npz(original/"writing/parent.npz",parent,root)
    study.save_npz(original/"writing/boundary.npz",boundary,root)
    study.save_npz(original/"intervention/bodies.npz",ranked,root)
    theta = dict(parent=parent["theta"],damaged=damaged)
    for arm,old in study.RECOVERY_ANCHORS.items():
        b,r = arm.split("_")
        v = ranked["donor_V"] if b == "ranked" else boundary[f"{b}_V"]
        initial = dict(V=v.copy(),ema=v.copy(),R=np.zeros_like(v),theta=damaged.copy())
        result = study.writing.recover(ctx,initial,study.writing.Mode(reader=r),parent,fresh)
        study.save_npz(writer/f"recovery_{old}.npz",result["raw"],root)
        theta[arm] = result["final"]["theta"]
    metadata = dict(tissue=tissue,passes=True,gates={"fixture":True},config=asdict(cfg),tissue_config=asdict(ctx["tissue"]),
                    source_parent_sha256=study.source.base.state_digest(parent),source_native_sha256=study.source.base.array_digest(ctx["native"]),
                    recovery_rng_final=result["rng_final"])
    study.strict_json(original/"writing/experiment.json",metadata,root)
    for arm,(folder,name) in study.ANCHORS.items():
        result = study.readout.assay(ctx,theta[arm].tobytes(),rcfg)
        directory = original/"readout" if folder == "ancestor" else previous
        study.save_npz(directory/f"readout_{name}.npz",result["raw"],root)
    study.strict_json(previous/"experiment.json",dict(tissue=tissue,passes=True,rng_final=result["rng_final"],birth_rng_final=result["birth_rng_final"]),root)
    cal,raw = study.readout.calibration(ctx,rcfg)
    study.strict_json(previous/"calibration.json",cal,root)
    for name,data in raw.items():
        study.save_npz(previous/f"calibration_{name}.npz",data,root)
    records,checked = {},{}
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(check,"TISSUES",(tissue,))
        mp.setattr(study,"checker",lambda:check)
        for stage in study.STAGES:
            records[stage],checked[stage] = study.execute_cell(root,tissue,stage,root/"result",cfg,rcfg)
    return dict(root=root,original=original,writer=writer,previous=previous,tissue=tissue,cfg=cfg,rcfg=rcfg,records=records,checked=checked)


@pytest.fixture(scope="module")
def example(tmp_path_factory,check):
    return build_fixture(tmp_path_factory.mktemp("actual-donor-fixture"),
        replace(study.CONFIG,sweeps=16,times=(0,1,8,16)),replace(study.READOUT_CONFIG,draws=2,sweeps=16,times=(0,1,16)),check)


def test_frozen_contract_and_required_sources(check,monkeypatch):
    c = study.contract()
    assert study.TISSUES == check.TISSUES == tuple(range(30040,30056))
    for key in ("MAIN","OFF","ARMS","PACKETS","RECOVERIES","RECOVERY_ANCHORS","ANCHORS"):
        assert getattr(study,key) == getattr(check,key)
    assert {k:tuple(v.items()) for k,v in study.CONTRASTS.items()} == check.TERMS
    assert c["new_training_lives"] == c["law_verdict_changes"] == 0 and c["new_writing_lives"] == 1024
    assert c["total_recovery_lives"]+c["total_readout_lives"] == c["total_executed_lives"] == 81920
    assert c["scored_readout_lives"]+c["replay_lives"]+c["calibration_lives"] == 77824
    assert c["output_hashes"] == 579 and c["workers"] == 4
    monkeypatch.setattr(study,"source_inputs",lambda root: [])
    paths = study.input_paths(Path("/unused"))
    assert Path(check.__file__).resolve() in paths and Path(study.__file__).resolve() in paths
    assert len(paths) == 6 and all(p.is_file() for p in paths)
    for arm in study.RECOVERIES:
        m = study.mode(arm)
        assert m.reader in ("native","damaged") and m.reference == "zero" and not m.hold
        assert m.write is (arm not in study.OFF)
    with pytest.raises(ValueError):
        study.mode("actual_live")


def test_transplant_only_values_correct_donor_and_shuffle(example,check):
    e = example
    boundary = check.common.arrays(e["original"]/"writing/boundary.npz")
    ranked = check.common.arrays(e["original"]/"intervention/bodies.npz")
    bodies = study.make_bodies(boundary,ranked,e["tissue"],e["cfg"])
    check.common.close(study.geometry(bodies,boundary["fresh"]),check.check_bodies(boundary,ranked,bodies,e["tissue"]))
    np.testing.assert_array_equal(bodies["actual_V"],study.source.donor(boundary["kept_V"],4))
    for b in study.BODIES:
        np.testing.assert_array_equal(bodies[f"{b}_V"][boundary["fresh"]],boundary["kept_V"][boundary["fresh"]])
    for i in range(16):
        mask = ~boundary["fresh"][i]
        np.testing.assert_array_equal(np.sort(bodies["actual_V"][i][mask]),np.sort(bodies["donorshuffled_V"][i][mask]))
    initials = study.initial_states(boundary,bodies)
    for state in initials.values():
        assert np.all(state["R"] == 0.)
        np.testing.assert_array_equal(state["ema"],state["V"])
        np.testing.assert_array_equal(state["theta"],boundary["damaged_theta"])


def test_extra_donor_addresses_rejected(example,check):
    e = example
    boundary = check.common.arrays(e["original"]/"writing/boundary.npz")
    ranked = check.common.arrays(e["original"]/"intervention/bodies.npz")
    bodies = study.make_bodies(boundary,ranked,e["tissue"],e["cfg"])
    bodies["donor_indices"] = np.append(bodies["donor_indices"],0)
    with pytest.raises(AssertionError):
        check.check_bodies(boundary,ranked,bodies,e["tissue"])


def test_saved_three_stage_cell_and_full_thousand_updates(example,tmp_path,check):
    assert len(list((example["root"]/"result").iterdir())) == 36
    assert example["checked"]["writing"]["historical_recovery_anchors"] == 6
    assert example["checked"]["readout"]["historical_readout_anchors"] == 7
    full = build_fixture(tmp_path,study.CONFIG,replace(study.READOUT_CONFIG,draws=2),check)
    assert full["checked"]["writing"]["recorded_batch_steps"] == 14000
    assert full["checked"]["readout"]["scored_readout_lives"] == 448


@pytest.mark.parametrize("kind",("body","fill","donor_index","shuffle","geometry","initial_theta","initial_R","reader", "R_recurrence",
                                "theta_axis","theta_scale","off_ema","recovery_anchor","curve","stratum","writer_summary","recovery_rng",
                                "packet","birth","readout_R","readout_theta","probability","donor_score","paired","wrong","off","readout_anchor","readout_rng","origin"))
def test_independent_saved_corruption_rejected(example,check,tmp_path,monkeypatch,kind):
    e = example
    output = tmp_path/"cell"
    shutil.copytree(e["root"]/"result",output)
    monkeypatch.setattr(check,"TISSUES",(e["tissue"],))
    writing_kinds = {"body","fill","donor_index","shuffle","geometry","initial_theta","initial_R","reader","R_recurrence", "theta_axis","theta_scale",
                     "off_ema","recovery_anchor","curve","stratum","writer_summary","recovery_rng"}
    json_kinds = {"geometry","writer_summary","recovery_rng","donor_score","paired","readout_rng","origin"}
    if kind in json_kinds:
        path = output/("writing.json" if kind in writing_kinds else "readout.json")
        record = json.loads(path.read_text())
        if kind == "geometry":
            record["geometry"]["actual"]["retained_rms"][0] += .1
        elif kind == "writer_summary":
            record["arms"]["actual_native"]["1"]["V"]["mean"]["donor_accuracy"] += .1
        elif kind == "recovery_rng":
            record["recovery_rng_final"]["actual_native"] = "0"*64
        elif kind == "donor_score":
            record["arms"]["actual_native"]["donor_accuracy"] += .1
        elif kind == "paired":
            record["paired"]["actual_minus_kept_native"]["donor"]["improved"] += .1
        elif kind == "readout_rng":
            record["rng_final"] = "0"*64
        else:
            record["packet_origin"] = "imported_donor_memory"
        study.strict_json(path,record,tmp_path)
    else:
        name,key = {"body":("bodies","actual_V"),"fill":("bodies","actual_V"),"donor_index":("bodies","donor_indices"),"shuffle":("bodies","permutations"),
                    "initial_theta":("recovery_actual_native","s0_theta"),"initial_R":("recovery_actual_native","s0_R"),"reader":("recovery_actual_native","fixed_reader"),
                    "R_recurrence":("recovery_actual_native","reference_trace"),"theta_axis":("recovery_actual_native","theta_trace"),
                    "theta_scale":("recovery_actual_native","projection_scale"),"off_ema":("recovery_actual_native_off","s1_ema"),
                    "recovery_anchor":("recovery_kept_native","s1_ema"),"curve":("writing","curves"),"stratum":("writing","strata"),
                    "packet":("packets","actual_native"),"birth":("readout_actual_native","s0_ema"),"readout_R":("readout_actual_native","s1_R"),
                    "readout_theta":("readout_actual_native","s1_theta"),"probability":("readout_actual_native","probabilities"),
                    "wrong":("readout_wrong","s1_ema"),"off":("readout_reader_off","s1_ema"),"readout_anchor":("readout_ranked_native","s1_ema")}[kind]
        path = output/f"{name}.npz"
        arrays = check.common.arrays(path)
        if kind in ("body","fill"):
            fresh = check.common.arrays(e["original"]/"writing/boundary.npz")["fresh"]
            pos = np.flatnonzero((fresh if kind == "fill" else ~fresh).ravel())[0]
            arrays[key].flat[pos] += .1
        elif kind == "theta_axis":
            arrays[key][2,0,5] += .1
        else:
            arrays[key].flat[0] += 1 if kind in ("donor_index","shuffle") else .1
        study.source.base.atomic_npz(path,arrays,tmp_path)
    with pytest.raises(AssertionError):
        if kind in writing_kinds:
            check.check_writing(e["original"],e["writer"],output,e["tissue"],asdict(e["cfg"]))
        else:
            check.check_readout(e["original"],e["previous"],output,e["tissue"],asdict(e["cfg"]),asdict(e["rcfg"]))


def test_pooled_observers_and_common_reader_shift(example,check):
    rows = [deepcopy(example["records"]["readout"]) | {"tissue":t} for t in study.TISSUES]
    wr = [deepcopy(example["records"]["writing"]) | {"tissue":t} for t in study.TISSUES]
    assert check.check_pool(rows,study.pooled(rows))
    assert check.check_writing_pool(wr,study.writing_pooled(wr,example["cfg"]),asdict(example["cfg"]))
    for r in rows:
        for arm in study.MAIN:
            value = .3 if arm.endswith("native") else .2
            r["arms"][arm].update(donor_accuracy=value,donor_message_accuracy=[value]*4)
    p = study.pooled(rows)
    assert p["contrasts"]["actual_native_minus_damaged"]["donor_accuracy"]["mean"] == pytest.approx(.1)
    assert p["contrasts"]["actual_specific_reader_interaction"]["donor_accuracy"]["mean"] == 0.
    assert check.check_pool(rows,p)
    p["contrasts"]["actual_minus_kept_native"]["donor_accuracy"]["positive"] = 16
    with pytest.raises(AssertionError):
        check.check_pool(rows,p)
    wp = study.writing_pooled(wr,example["cfg"])
    wp["contrasts"]["actual_minus_ranked_native"]["mean"][0][0][4] += .1
    with pytest.raises(AssertionError):
        check.check_writing_pool(wr,wp,asdict(example["cfg"]))
    for fn,data in ((study.pooled,rows),(study.writing_pooled,wr)):
        with pytest.raises(ValueError):
            fn(data[:-1])


def prepared(root,monkeypatch,detached=False):
    path = root/"fixture.txt"
    study.atomic_text(path,"frozen fixture",root)
    monkeypatch.setattr(study,"input_paths",lambda _: [path])
    monkeypatch.setattr(study,"preflight",lambda _: [0,1,2,3])
    seconds = 30. if detached else 2.
    timing = dict(run_id=study.RUN_ID,passes=True,must_detach=detached,tissue_seconds=seconds,
                  projected_seconds=seconds*24+90,input_sha256={str(path):study.sha256_file(path)})
    study.strict_json(study.timing_path(root),timing,root)
    study.prepare(root)
    return root/"runs"/study.RUN_ID


@pytest.mark.parametrize("key,value",(("workers",5),("new_writing_lives",2048),("scored_readout_lives",60000),("direction_tolerance",.1)))
def test_changed_contract_rejected(tmp_path,monkeypatch,key,value):
    run = prepared(tmp_path,monkeypatch)
    record = json.loads((run/"MANIFEST.json").read_text())
    record[key] = value
    study.strict_json(run/"MANIFEST.json",record,tmp_path)
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


def test_detachment_required_exclusive_and_no_polling(tmp_path,monkeypatch):
    run = prepared(tmp_path,monkeypatch,True)
    with pytest.raises(RuntimeError,match="detached"):
        study.run_study(tmp_path)
    assert not (run/"EXECUTION.lock").exists()
    calls = []
    def launch(command,**kwargs):
        calls.append((command,kwargs))
        return SimpleNamespace(pid=12345)
    monkeypatch.setattr(study.subprocess,"Popen",launch)
    result = study.detach(tmp_path)
    assert result["polling_owner"] == "user" and result["pid"] == 12345
    assert len(calls) == 1 and calls[0][1]["start_new_session"] is True
    assert "laws_confirmation.l22_actual_donor_body" in calls[0][0]
    with pytest.raises(FileExistsError):
        study.detach(tmp_path)


def test_calibration_failure_prevents_writing_and_readout(tmp_path,monkeypatch):
    run = prepared(tmp_path,monkeypatch)
    stages = []
    def bad_cells(root,output,stage):
        stages.append(stage)
        for t in study.TISSUES:
            yield t,(dict(tissue=t,passes=True,gates={"fixture":True},positive_accuracy=.25),dict(tissue=t,passes=True))
    monkeypatch.setattr(study,"cells",bad_cells)
    with pytest.raises(RuntimeError,match="calibration"):
        study.run_study(tmp_path)
    assert stages == ["calibration"] and (run/"FAILED").exists() and not (run/"COMPLETE").exists()
    with pytest.raises(AssertionError):
        study.run_study(tmp_path)


def test_successful_three_stage_publication(example,tmp_path,monkeypatch,check):
    run = prepared(tmp_path,monkeypatch)
    stages = []
    def fake_cells(root,output,stage):
        stages.append(stage)
        for t in reversed(study.TISSUES):
            directory = output/f"tissue_{t}"
            if stage == "calibration":
                directory.mkdir()
                record = dict(tissue=t,passes=True,gates={"fixture":True},positive_accuracy=1.)
                names = ["calibration_positive","calibration_reader_off"]
                filename = "calibration.json"
            elif stage == "writing":
                record = deepcopy(example["records"]["writing"]) | {"tissue":t}
                for arm in study.MAIN:
                    record["arms"][arm] = {str(s):deepcopy(record["arms"][arm]["0"]) for s in study.STEPS}
                names = [*[f"recovery_{a}" for a in study.RECOVERIES],"bodies","writing"]
                filename = "writing.json"
            else:
                record = deepcopy(example["records"]["readout"]) | {"tissue":t}
                names = [*[f"readout_{a}" for a in study.ARMS],"packets"]
                filename = "readout.json"
            for name in names:
                study.save_npz(directory/f"{name}.npz",{"fixture":np.zeros(1)},root)
            study.strict_json(directory/filename,record,root)
            yield t,(record,dict(tissue=t,passes=True))
    monkeypatch.setattr(study,"cells",fake_cells)
    assert study.run_study(tmp_path) == 0 and stages == list(study.STAGES)
    assert (run/"COMPLETE").is_file() and not (run/"FAILED").exists()
    assert check.common.manifest_check(tmp_path/"outputs"/study.RUN_ID/"output_hashes.sha256") == 579
    with pytest.raises(AssertionError):
        study.run_study(tmp_path)


@pytest.mark.parametrize("bad",(float("nan"),np.bool_(True)))
def test_invalid_json_not_published(tmp_path,bad):
    path = tmp_path/"bad.json"
    with pytest.raises((TypeError,ValueError)):
        study.strict_json(path,{"value":bad},tmp_path)
    assert not path.exists()
