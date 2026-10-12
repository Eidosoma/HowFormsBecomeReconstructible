from copy import deepcopy
from dataclasses import asdict
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from laws_confirmation import l22_source_recovery as study


@pytest.fixture(scope="module")
def checker():
    path = Path(__file__).resolve().parents[1]/"scripts/audit_l22_source_recovery_outputs.py"
    spec = importlib.util.spec_from_file_location("l22_source_checker_tests",path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def example():
    cfg = study.Config(replicates=1,settle=4,imprint=8,sweeps=12,times=(0,4,8,12))
    ctx = study.context(40071,cfg)
    result,artifacts = study.experiment(ctx)
    return ctx,result,artifacts


def test_registry_and_native_parameters():
    c = study.contract()
    assert len(study.ARMS)==18 and len(study.PROBES)==21 and len(study.ENDPOINTS)==4
    assert study.TISSUES==tuple(range(30000,30008)) and c["workers"]==4
    assert c["config"]["damage"]==.3 and c["config"]["lam"]==.001
    assert c["quantiles"]==[.00625,.99375] and c["law_verdict_changes"]==0
    assert c["recovery_lives"]==2304 and c["assay_lives"]==2688


def test_source_anchors_replays_and_all_small_conditions(example):
    ctx,result,artifacts = example
    assert result["passes"] and all(result["gates"].values())
    assert set(result["recovery"])==set(study.ARMS) and set(result["probe"])==set(study.PROBES)
    assert len(artifacts)==42
    assert all(study.base.message_independent(v,1) for v in artifacts["before"].values())


def test_independent_boundaries_and_every_projection(example,checker):
    ctx,result,artifacts = example
    b,parent = artifacts["boundary"],artifacts["parent"]
    fresh = checker.check_boundary(parent,b,ctx["index"],asdict(ctx["config"]),asdict(ctx["tissue"]))
    for arm,mode in study.MODES.items():
        initial = study.initial_state(ctx,parent,{k:b[f"kept_{k}"] for k in study.KEYS},b["scrambled_V"],b["damaged_theta"],mode)
        checker.check_recovery(artifacts[f"recovery_{arm}"],initial,parent,fresh,asdict(mode),asdict(ctx["config"]),result["recovery"][arm])


@pytest.mark.parametrize("kind",("theta_trace","target_trace","reference_trace","projection_scale","target_energy","snapshot","initial"))
def test_independent_writer_tampering_is_detected(kind,example,checker):
    ctx,result,artifacts = deepcopy(example)
    b,parent = artifacts["boundary"],artifacts["parent"]
    raw = artifacts["recovery_body_only"]
    mode = study.MODES["body_only"]
    initial = study.initial_state(ctx,parent,{k:b[f"kept_{k}"] for k in study.KEYS},b["scrambled_V"],b["damaged_theta"],mode)
    if kind=="snapshot":
        raw["s12_theta"][0,0,0]+=.1
    elif kind=="initial":
        raw["s0_R"][0,0,0]=.1
    else:
        raw[kind].flat[5]+=.1
    with pytest.raises(AssertionError):
        checker.check_recovery(raw,initial,parent,b["fresh"],asdict(mode),asdict(ctx["config"]),result["recovery"]["body_only"])


def test_held_reference_restoration_ignores_body_and_writer_off_is_exact(example):
    ctx,result,a = example
    for s in ctx["config"].times:
        np.testing.assert_array_equal(a["recovery_held_kept"][f"s{s}_theta"],a["recovery_held_scrambled"][f"s{s}_theta"])
        for arm,mode in study.MODES.items():
            if not mode.write:
                np.testing.assert_array_equal(a[f"recovery_{arm}"][f"s{s}_theta"],a[f"recovery_{arm}"]["s0_theta"])
    assert not np.array_equal(a["recovery_held_kept"]["s12_V"],a["recovery_held_scrambled"]["s12_V"])


def test_assay_only_receives_theta_and_paired_naive_birth(example,checker):
    ctx,result,a = example
    for name in study.PROBES:
        raw = a[f"probe_{name}"]
        for key in ("V","ema","R"):
            np.testing.assert_array_equal(raw[f"s0_{key}"],study.assay_birth(ctx)[key])
        for s in ctx["config"].times:
            np.testing.assert_array_equal(raw[f"s{s}_theta"],raw["s0_theta"])
            assert np.all(raw[f"s{s}_R"]==0.)
            measured = checker.metrics({k:raw[f"s{s}_{k}"] for k in study.KEYS},a["parent"],np.ones_like(a["boundary"]["fresh"]),1)
            checker.close(result["probe"][name][str(s)],measured)
    assert result["probe"]["reader_off"]["12"]["mean"]["V_accuracy"]==.25
    for bad in (b"wrong",None,np.zeros((4,16,16)),np.full((4,16,16),np.nan).tobytes()):
        with pytest.raises(ValueError):
            study.assay(ctx,bad)


def test_json_metrics_remain_numeric(example,tmp_path,checker):
    value = example[1]
    study.atomic_json(tmp_path/"result.json",value,tmp_path)
    loaded = json.loads((tmp_path/"result.json").read_text())
    checker.close(loaded,json.loads(json.dumps(value)))
    assert type(loaded["recovery"]["body_only"]["12"]["rows"][0]["world"]) is int


def positive_rows():
    rows=[]
    for tissue in study.TISSUES:
        values={a:{"1000":{"mean":{"theta_corr_parent":.3,"V_accuracy":.25}}} for a in study.PROBES}
        values["parent"]["1000"]["mean"]["V_accuracy"]=1.
        values["body_only"]["1000"]["mean"]={"theta_corr_parent":.6,"V_accuracy":.75}
        rows.append({"tissue":tissue,"passes":True,"gates":{"checked":True},"recovery":deepcopy(values),"probe":values})
    return rows


def test_fixed_endpoints_parent_floor_and_six_tissue_rule():
    rows=positive_rows()
    assert study.classify(rows)["label"]=="BODY_INFORMATION_SUPPORTS_RECOVERY"
    for r in rows[-3:]:
        r["probe"]["body_only"]["1000"]["mean"]["V_accuracy"] = .25
    result=study.classify(rows)
    assert result["label"]=="NO_QUALIFIED_BODY_ROUTE_LEAD"
    assert result["co_primary"]["body_readout_vs_scramble"]["positive_tissues"]==5
    rows=positive_rows()
    rows[0]["probe"]["parent"]["1000"]["mean"]["V_accuracy"] = .25
    assert study.classify(rows)["label"]=="PARENT_THETA_NOT_READABLE"
    assert study.classify(rows[:-1])["label"]=="INVALID_STRUCTURAL_FAILURE"


def test_calibration_floor_does_not_select_new_norm(example):
    ctx=example[0]
    result,raw=study.calibration(ctx)
    assert result["passes"] and set(raw)=={"positive","reader_off"}
    rows=[result|{"tissue":t,"positive_accuracy":1.} for t in study.TISSUES]
    assert study.calibrated(rows)
    rows[0]["positive_accuracy"]=.25
    assert not study.calibrated(rows)


def test_long_execution_requires_detach_and_never_polls(tmp_path,monkeypatch):
    run=tmp_path/"runs"/study.RUN_ID
    run.mkdir(parents=True)
    (tmp_path/"logs").mkdir()
    monkeypatch.setattr(study,"verify_prepared",lambda root:{"benchmark":{"must_detach":True,"projected_seconds":901}})
    with pytest.raises(RuntimeError,match="detached"):
        study.run_study(tmp_path)
    calls=[]
    def spawn(command,**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(pid=40070)
    monkeypatch.setattr(study.subprocess,"Popen",spawn)
    assert study.detach(tmp_path)["polling_owner"]=="user"
    assert calls[0]["start_new_session"] and calls[0]["stdin"]==study.subprocess.DEVNULL
    with pytest.raises(FileExistsError):
        study.detach(tmp_path)


def test_body_only_cannot_read_damaged_theta(example):
    ctx,result,a=example
    b,parent=a["boundary"],a["parent"]
    mode=study.MODES["body_only"]
    initial=study.initial_state(ctx,parent,{k:b[f"kept_{k}"] for k in study.KEYS},b["scrambled_V"],b["damaged_theta"],mode)
    initial["theta"]=-initial["theta"]
    changed=study.recover(ctx,initial,mode,parent,b["fresh"])
    for s in ctx["config"].times:
        for k in ("V","ema","R"):
            np.testing.assert_array_equal(changed["raw"][f"s{s}_{k}"],a["recovery_body_only"][f"s{s}_{k}"])
    assert not np.array_equal(changed["final"]["theta"],a["recovery_body_only"]["s12_theta"])


def test_complete_saved_cell_audit_and_independent_endpoints(example,checker,tmp_path):
    ctx,result,artifacts=example
    checker.close({a:asdict(m) for a,m in study.MODES.items()},checker.modes())
    for name,raw in artifacts.items():
        study.base.atomic_npz(tmp_path/f"{name}.npz",raw,tmp_path)
    checked=checker.check_tissue(tmp_path,result,asdict(ctx["config"]))
    assert len(checked["recovery"])==18 and len(checked["probe"])==21
    rows=positive_rows()
    small=[{"tissue":r["tissue"],**{stage:{a:{t:v["mean"] for t,v in times.items()} for a,times in r[stage].items()}
             for stage in ("recovery","probe")}} for r in rows]
    checker.close(study.classify(rows),checker.adjudicate(small))
    cal,fields=study.calibration(ctx)
    for name,raw in fields.items():
        study.base.atomic_npz(tmp_path/f"calibration_{name}.npz",raw,tmp_path)
    assert checker.check_calibration(tmp_path,cal,asdict(ctx["config"]))==cal["positive_accuracy"]


def test_prepared_input_and_parameter_immutability(tmp_path,monkeypatch):
    run=tmp_path/"runs"/study.RUN_ID
    run.mkdir(parents=True)
    input_file=tmp_path/"source.txt"
    study.atomic_text(input_file,"frozen",tmp_path)
    study.atomic_json(study.benchmark_path(tmp_path),{"passes":True},tmp_path)
    monkeypatch.setattr(study,"input_paths",lambda:[input_file])
    hashes={str(p):study.sha256_file(p) for p in (input_file,study.benchmark_path(tmp_path))}
    manifest=study.contract()|{"input_sha256":hashes,"hash_contract":study.canonical_digest(hashes)}
    study.atomic_json(run/"MANIFEST.json",manifest,tmp_path)
    study.atomic_json(run/"STATUS.json",{"status":"PREPARED"},tmp_path)
    assert study.verify_prepared(tmp_path)["workers"]==4
    study.atomic_json(run/"MANIFEST.json",manifest|{"workers":5},tmp_path)
    with pytest.raises(RuntimeError,match="contract changed"):
        study.verify_prepared(tmp_path)
    study.atomic_json(run/"MANIFEST.json",manifest,tmp_path)
    study.atomic_text(input_file,"tampered",tmp_path)
    with pytest.raises(RuntimeError,match="contract changed"):
        study.verify_prepared(tmp_path)
    with pytest.raises(FileExistsError):
        study.prepare(tmp_path)


def test_failed_calibration_stops_before_parents(tmp_path,monkeypatch):
    from concurrent.futures import Future
    run=tmp_path/"runs"/study.RUN_ID
    run.mkdir(parents=True)
    monkeypatch.setattr(study,"verify_prepared",lambda root:{"benchmark":{"must_detach":False},"input_sha256":{}})
    monkeypatch.setattr(study,"runtime",lambda:{"passes":True})
    monkeypatch.setattr(study,"disk_preflight",lambda root:{"passes":True})
    monkeypatch.setattr(study.base,"verify_hashes",lambda hashes:True)
    calls=[]
    class Pool:
        def __init__(self,**kwargs):
            assert kwargs["max_workers"]==4
        def __enter__(self):
            return self
        def __exit__(self,*args):
            return False
        def submit(self,fn,index,root_text,stage):
            calls.append(stage)
            assert stage=="calibration"
            future=Future()
            future.set_result({"tissue":index,"passes":True,"positive_accuracy":.25,"gates":{"checked":True}})
            return future
    monkeypatch.setattr(study,"ProcessPoolExecutor",Pool)
    assert study.run_study(tmp_path)==0
    status=json.loads((run/"STATUS.json").read_text())
    assert status["classification"]=="INSTRUMENT_NOT_QUALIFIED" and status["completed_tissues"]==0
    assert len(calls)==8 and (run/"COMPLETE").is_file()


def test_runtime_failure_marks_failed(tmp_path,monkeypatch):
    run=tmp_path/"runs"/study.RUN_ID
    run.mkdir(parents=True)
    monkeypatch.setattr(study,"verify_prepared",lambda root:{"benchmark":{"must_detach":False}})
    monkeypatch.setattr(study,"runtime",lambda:{"passes":False})
    with pytest.raises(RuntimeError,match="runtime/storage"):
        study.run_study(tmp_path)
    assert (run/"FAILED").is_file() and not (run/"COMPLETE").exists()
