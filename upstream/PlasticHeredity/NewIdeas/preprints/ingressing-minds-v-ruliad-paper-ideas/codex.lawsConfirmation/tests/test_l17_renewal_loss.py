from copy import deepcopy
import importlib.util
import inspect
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from laws_confirmation import l17_renewal_loss as study


@pytest.fixture(scope="module")
def independent():
    path = Path(__file__).resolve().parents[1]/"scripts/audit_l17_renewal_loss_outputs.py"
    spec = importlib.util.spec_from_file_location("loss_independent_tests",path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def field(amplitude=1., replicates=2):
    return np.repeat(study.templates(),replicates,axis=0)*amplitude


def synthetic_raw(replicates=2, signal=True):
    code = field(1.,replicates)
    shared = np.broadcast_to(.3*study.templates()[0]+.1,code.shape).copy()
    incoming = shared+.8*code if signal else shared.copy()
    q = np.zeros_like(incoming)
    raw = {"s0_V":shared.copy(),"s0_ema":shared.copy(),"s0_R":incoming.copy(),"s0_Q":q.copy()}
    trace = [study.scores(shared,study.templates())]
    for step in range(1,1001):
        body = shared+(.2+.2*step/1000)*code if signal else shared.copy()
        q = q+.002*(body-q)
        trace.append(study.scores(body,study.templates()))
        if step in (50,1000):
            raw.update({f"s{step}_V":body.copy(),f"s{step}_ema":body.copy(),f"s{step}_R":incoming.copy(),f"s{step}_Q":q.copy()})
    raw["body_scores"] = np.asarray(trace)
    return raw


@pytest.fixture(scope="module")
def example():
    raw,reset = synthetic_raw(),synthetic_raw(signal=False)
    return raw,reset,study.analyze_arm(raw,reset,replicates=2)


def test_contract_scope_is_retained_data_only():
    c = study.contract()
    assert c["new_simulations"]==c["law_verdict_changes"]==0 and study.WORKERS==4
    assert study.TISSUES==tuple(range(10000,10008)) and study.GENERATIONS==tuple(range(1,13))
    assert len(study.ARMS)==9 and study.RHO==.002 and study.LATE==(751,1000)
    assert c["baselines"]["protected_copy"]=="split_reset" and c["baselines"]["native_carry"]=="native_reset"
    assert "blueprint_step" not in inspect.getsource(study)


def test_pure_attenuation_and_shared_background_do_not_become_shape_error():
    incoming = field(.8)
    outgoing = .5*incoming+np.broadcast_to(study.templates()[1]*.7+.1,incoming.shape)
    result = study.transfer_metrics(incoming,outgoing,2)
    for r in result["per_replicate"]:
        assert r["aligned_gain"]==pytest.approx(.5) and r["cosine"]==pytest.approx(1.)
        assert r["input_message_rms"]==pytest.approx(.8) and r["output_message_rms"]==pytest.approx(.4)
        assert r["residual_rms"]<1e-14


def test_rotation_detected_separately_from_total_size():
    incoming = field()
    outgoing = np.roll(incoming,2,axis=2)
    result = study.transfer_metrics(incoming,outgoing,2)["mean"]
    assert result["aligned_gain"]==pytest.approx(0.) and result["cosine"]==pytest.approx(0.)
    assert result["residual_rms"]==pytest.approx(1.) and result["residual_energy_fraction"]==pytest.approx(1.)


def test_common_pattern_can_mask_signal_without_destroying_oracle_contrast():
    original = field(.2)+3*study.templates()[0]
    before = original.copy()
    result = study.field_metrics(original,study.templates(),2)["mean"]
    assert result["raw_accuracy"]==.25 and result["oracle_centered_accuracy"]==1.
    assert result["message_rms"]==pytest.approx(.2) and result["common_rms"]==pytest.approx(3.)
    assert result["message_energy_fraction"]==pytest.approx(.04/9.04)
    np.testing.assert_array_equal(original,before)


def test_zero_contrast_has_undefined_gains_not_artificial_zero_capacity():
    zero = np.zeros_like(field())
    result = study.field_metrics(zero,study.templates(),2)["mean"]
    assert result["raw_accuracy"]==result["oracle_centered_accuracy"]==.25
    assert result["message_energy_fraction"] is None and result["valid_counts"]["message_energy_fraction"]==0
    for outgoing in (zero,field()):
        transfer = study.transfer_metrics(zero,outgoing,2)["mean"]
        assert transfer["aligned_gain"] is None and transfer["cosine"] is None
    same = np.broadcast_to(np.random.default_rng(409).normal(size=(2,16,16)),(4,2,16,16)).reshape(8,16,16).copy()
    assert np.all(study.contrast_parts(same,2)[1]==0.)


def test_energy_reconstruction_and_nonfinite_shape_guards():
    rng = np.random.default_rng(17)
    data = rng.normal(size=(8,16,16))
    common,contrast = study.contrast_parts(data,2)
    np.testing.assert_allclose(common+contrast,data.reshape(4,2,16,16),rtol=0.,atol=1e-14)
    assert np.mean(data**2)==pytest.approx(np.mean(common**2)+np.mean(contrast**2))
    for invalid in (data[:4],np.full_like(data,np.nan)):
        with pytest.raises(ValueError):
            study.contrast_parts(invalid,2)


def test_reset_resemblance_and_reference_reset_guard():
    signal = field(.4)
    reset = np.broadcast_to(study.templates()[0]+.1,signal.shape).copy()
    result = study.background_metrics(signal+reset,reset,2)["mean"]
    assert result["common_reset_cosine"]==pytest.approx(1.) and result["common_minus_reset_rms"]<1e-14
    assert result["whole_minus_reset_rms"]==pytest.approx(.4)
    with pytest.raises(ValueError,match="reset contains"):
        study.background_metrics(signal,signal,2)


def history_case(mode):
    base = field()
    q = np.zeros_like(base)
    trace = [study.scores(q,study.templates())]
    for s in range(1,1001):
        if mode=="constant":
            body = .5*base
        elif mode=="late_only":
            body = base if s>500 else np.zeros_like(base)
        elif mode=="early_only":
            body = base if s<=500 else np.zeros_like(base)
        else:
            body = np.broadcast_to(study.templates()[0]+(2 if s<=500 else -2)*study.templates()[1],base.shape)
        q = q+.002*(body-q)
        trace.append(study.scores(body,study.templates()))
    return np.asarray(trace),base,q


@pytest.mark.parametrize("mode",("constant","late_only","early_only","changing_competitor"))
def test_exact_time_budget_and_independent_recurrence(mode,independent):
    trace,incoming,q = history_case(mode)
    result = study.writer_metrics(trace,incoming,q,study.templates(),2)
    check = independent.writer_check(trace,incoming,q,2)
    independent.close(result,check)
    assert result["total_weight"]==pytest.approx(1-.998**1000)
    assert sum(b["weight_mass"] for b in result["bands"])==pytest.approx(result["total_weight"])
    budget = result["budget_mean"]
    assert budget["input_to_candidate_change"]==pytest.approx(sum(budget[k] for k in ("input_to_late_body_change","finite_weight_loss","history_vs_late_change")))
    if mode=="constant":
        assert budget["input_to_late_body_change"]==pytest.approx(.5)
        assert budget["finite_weight_loss"]==pytest.approx(.5*.998**1000)
        assert abs(budget["history_vs_late_change"])<1e-12
    elif mode=="late_only":
        assert budget["history_vs_late_change"]>0
    elif mode=="early_only":
        assert budget["history_vs_late_change"]<0
    else:
        actual = result["budget_per_world"][0]["candidate_margin"]
        weights = .002*.998**np.arange(999,-1,-1)
        instantaneous = np.sum(weights*(trace[1:,0,0]-trace[1:,0,1:].max(axis=1)))
        assert abs(actual-instantaneous)>.5
        assert result["bands"][0]["per_world"][0]["competitor"]==3


def test_writer_rejects_nonpartition_and_changed_unsaved_projection():
    trace,incoming,q = history_case("constant")
    with pytest.raises(ValueError,match="partition"):
        study.writer_metrics(trace,incoming,q,study.templates(),2,bands=((1,500),(500,1000)))
    trace[2,0,0]+=.1
    with pytest.raises(AssertionError):
        study.writer_metrics(trace,incoming,q,study.templates(),2)


def test_independent_full_arm_and_json_roundtrip(example,independent,tmp_path):
    raw,reset,result = example
    study.atomic_json(tmp_path/"arm.json",result,tmp_path)
    saved = json.loads((tmp_path/"arm.json").read_text())
    assert type(saved["writer"]["bands"][0]["per_world"][0]["world"]) is int
    assert type(saved["writer"]["budget_per_world"][0]["replicate"]) is int
    checked = independent.check_arm(raw,reset,saved,replicates=2)
    independent.close(checked,study.small_summary(saved))
    assert len(result["fields"])==5 and len(result["transfers"])==3


@pytest.mark.parametrize("kind",("gain","energy","budget","oracle","competitor","zero_birth","unsaved_trace"))
def test_independent_tamper_detection(kind,example,independent):
    raw,reset,result = deepcopy(example)
    if kind=="gain":
        result["transfers"]["input_to_candidate"]["per_replicate"][0]["aligned_gain"]+=.01
    elif kind=="energy":
        result["fields"]["candidate_1000"]["mean"]["message_energy_fraction"]+=.01
    elif kind=="budget":
        result["writer"]["budget_per_world"][0]["history_vs_late_change"]+=.01
    elif kind=="oracle":
        result["fields"]["candidate_1000"]["per_replicate"][0]["oracle_centered_accuracy"]-=.1
    elif kind=="competitor":
        result["writer"]["bands"][0]["per_world"][0]["competitor"]=99
    elif kind=="zero_birth":
        raw["s0_Q"][0,0,0]=.1
    else:
        raw["body_scores"][2,0,0]+=.01
    with pytest.raises(AssertionError):
        independent.check_arm(raw,reset,result,replicates=2)


def test_equal_tissue_pooling_and_valid_denominators(example,independent):
    records = [{"tissue":t,"generation":g,"passes":True,"arms":{a:example[2] for a in study.ARMS}} for t in study.TISSUES for g in study.GENERATIONS]
    pooled = study.pooled_summary(records)
    expected = independent.pool_nodes([study.small_summary(example[2])]*8)
    independent.close(pooled["1"]["split_replace"],expected)
    assert pooled["12"]["split_replace"]["fields"]["candidate_1000"]["valid_tissues"]["raw_accuracy"]==8
    for invalid in (records[:-1],records+[records[0]]):
        with pytest.raises(ValueError,match="missing, duplicated"):
            study.pooled_summary(invalid)


def test_existing_output_blocks_benchmark_and_prepare(tmp_path):
    (tmp_path/"outputs"/study.RUN_ID).mkdir(parents=True)
    for fn in (study.prepare,study.benchmark):
        with pytest.raises(FileExistsError):
            fn(tmp_path)


def test_prepared_contract_hashes_and_parameter_tamper(tmp_path,monkeypatch):
    run = tmp_path/"runs"/study.RUN_ID
    run.mkdir(parents=True)
    path,bench = tmp_path/"input.txt",study.benchmark_path(tmp_path)
    study.atomic_text(path,"frozen",tmp_path)
    study.atomic_json(bench,{"must_detach":False},tmp_path)
    monkeypatch.setattr(study,"input_paths",lambda root:[path])
    hashes = {str(p):study.sha256_file(p) for p in (path,bench)}
    manifest = study.contract()|{"input_sha256":hashes,"hash_contract":study.canonical_digest(hashes)}
    study.atomic_json(run/"MANIFEST.json",manifest,tmp_path)
    study.atomic_json(run/"STATUS.json",{"status":"PREPARED"},tmp_path)
    assert study.verify_prepared(tmp_path)["workers"]==4
    for key,value in (("rho",.01),("late_window",[501,1000]),("workers",5),("generations",[1,2,3])):
        study.atomic_json(run/"MANIFEST.json",manifest|{key:value},tmp_path)
        with pytest.raises(RuntimeError,match="contract changed"):
            study.verify_prepared(tmp_path)
    study.atomic_json(run/"MANIFEST.json",manifest,tmp_path)
    study.atomic_text(path,"changed",tmp_path)
    with pytest.raises(RuntimeError,match="contract changed"):
        study.verify_prepared(tmp_path)


def test_long_run_requires_detach_and_detach_does_not_poll(tmp_path,monkeypatch):
    run = tmp_path/"runs"/study.RUN_ID
    run.mkdir(parents=True)
    (tmp_path/"logs").mkdir()
    monkeypatch.setattr(study,"verify_prepared",lambda root:{"benchmark":{"must_detach":True,"projected_seconds":901}})
    with pytest.raises(RuntimeError,match="detached launch required"):
        study.run_study(tmp_path)
    calls=[]
    def popen(command,**kwargs):
        calls.append((command,kwargs))
        return SimpleNamespace(pid=12009)
    monkeypatch.setattr(study.subprocess,"Popen",popen)
    result = study.launch_detached(tmp_path)
    assert result["pid"]==12009 and result["polling_owner"]=="user"
    assert calls[0][1]["start_new_session"] and calls[0][1]["stdin"]==study.subprocess.DEVNULL
    with pytest.raises(FileExistsError):
        study.launch_detached(tmp_path)


def test_runtime_failure_marks_failed_without_analysis(tmp_path,monkeypatch):
    run = tmp_path/"runs"/study.RUN_ID
    run.mkdir(parents=True)
    monkeypatch.setattr(study,"verify_prepared",lambda root:{"benchmark":{"must_detach":False}})
    monkeypatch.setattr(study,"runtime",lambda:{"passes":False})
    monkeypatch.setattr(study,"worker",lambda *args:pytest.fail("must not analyze"))
    with pytest.raises(RuntimeError,match="runtime/storage"):
        study.run_study(tmp_path)
    assert (run/"FAILED").is_file() and not (run/"COMPLETE").exists()
