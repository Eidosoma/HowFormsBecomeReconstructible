import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from laws_confirmation import l22_source_recovery as experiment


@pytest.fixture(scope="module")
def recovery():
    path=Path(__file__).resolve().parents[1]/"scripts/recover_l22_source_recovery_publication.py"
    spec=importlib.util.spec_from_file_location("l22_publication_tests",path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_reproduces_original_boolean_reporting_failure_and_strict_fix(recovery,tmp_path):
    rows=[{"tissue":t,"passes":True,"positive_accuracy":1.} for t in experiment.TISSUES]
    value=experiment.calibrated(rows)
    assert isinstance(value,np.bool_)
    with pytest.raises(TypeError):
        json.dumps({"calibration_qualified":value})
    with pytest.raises(TypeError):
        recovery.strict_json(tmp_path/"bad.json",{"calibration_qualified":value},tmp_path)
    assert not (tmp_path/"bad.json").exists()
    recovery.strict_json(tmp_path/"good.json",{"calibration_qualified":bool(value)},tmp_path)
    assert json.loads((tmp_path/"good.json").read_text())["calibration_qualified"] is True
    with pytest.raises(ValueError):
        recovery.strict_json(tmp_path/"nan.json",{"value":float("nan")},tmp_path)


@pytest.fixture
def source_tree(recovery,tmp_path,monkeypatch):
    run,out=tmp_path/"runs"/recovery.SOURCE_ID,tmp_path/"outputs"/recovery.SOURCE_ID
    failure={"status":"FAILED","error":"Object of type bool is not JSON serializable", "traceback":"print(json.dumps(status,indent=2),flush=True)"}
    recovery.strict_json(run/"STATUS.json",failure,tmp_path)
    recovery.atomic_text(run/"COMPLETE","2026-09-08T10:29:52.940272+00:00\n",tmp_path)
    recovery.atomic_text(run/"FAILED","2026-09-08T10:29:52.940837+00:00\n",tmp_path)
    rows=[{"tissue":t,"passes":True,"gates":{"verified":True}} for t in range(30000,30008)]
    study={"completed_cleanly":True,"calibration_qualified":"True","results":rows,"calibrations":rows}
    recovery.strict_json(out/"source_recovery.json",study,tmp_path)
    cfg={"replicates":4,"settle":120,"imprint":1000,"sweeps":1000,"times":[0,50,250,500,1000],"norm":.3,"lam":.001,"damage":.3}
    recovery.strict_json(run/"MANIFEST.json",{"config":cfg,"modes":recovery.audit.modes(),"tissues":list(range(30000,30008)),"workers":4},tmp_path)
    monkeypatch.setattr(recovery.audit,"manifest_check",lambda p:133 if p.name=="input_hashes.sha256" else 370)
    return tmp_path,run,out,failure,study


def test_forensic_qualification_preserves_source(source_tree,recovery):
    root,run,out,_,_=source_tree
    before={str(p):p.read_bytes() for directory in (run,out) for p in directory.iterdir()}
    result=recovery.source(root)
    assert result[3]==[133,370]
    assert {str(p):p.read_bytes() for directory in (run,out) for p in directory.iterdir()}==before


@pytest.mark.parametrize("damage",("error","location","marker","calibration","missing_tissue","gate","hashes"))
def test_forensic_guard_rejects_other_failures(damage,source_tree,recovery,monkeypatch):
    root,run,out,failure,study=source_tree
    if damage=="error":
        failure["error"]="scientific simulation failed"
    elif damage=="location":
        failure["traceback"]="earlier numerical calculation failed"
    elif damage=="marker":
        recovery.atomic_text(run/"COMPLETE","9999\n",root)
    elif damage=="calibration":
        study["calibration_qualified"]="False"
    elif damage=="missing_tissue":
        study["results"]=study["results"][:-1]
    elif damage=="gate":
        study["results"][0]["gates"]["verified"]=False
    else:
        monkeypatch.setattr(recovery.audit,"manifest_check",lambda p:0)
    recovery.strict_json(run/"STATUS.json",failure,root)
    recovery.strict_json(out/"source_recovery.json",study,root)
    with pytest.raises(AssertionError):
        recovery.source(root)


def test_detach_has_unique_lock_and_no_poll(recovery,tmp_path,monkeypatch):
    run=tmp_path/"runs"/recovery.RUN_ID
    run.mkdir(parents=True)
    (tmp_path/"logs").mkdir()
    monkeypatch.setattr(recovery,"verify",lambda root:{"benchmark":{"must_detach":True,"projected_seconds":901}})
    with pytest.raises(RuntimeError,match="detached"):
        recovery.run_recovery(tmp_path)
    calls=[]
    def spawn(cmd,**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(pid=70070)
    monkeypatch.setattr(recovery.subprocess,"Popen",spawn)
    record=recovery.detach(tmp_path)
    assert record["polling_owner"]=="user" and calls[0]["start_new_session"]
    with pytest.raises(FileExistsError):
        recovery.detach(tmp_path)
    with pytest.raises(FileExistsError):
        recovery.prepare(tmp_path)
