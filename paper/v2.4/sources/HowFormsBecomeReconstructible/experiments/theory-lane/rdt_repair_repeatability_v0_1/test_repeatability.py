"""Counterexamples, exact expectation checks and bounded execution safeguards."""
import copy
import itertools
import math
from pathlib import Path
import subprocess
import sys
import time
import numpy as np
import pytest
from rr_common import ROOT,C,read,ev,inherited,actions,fixtures,Guard
import rr_analysis as primary
import rr_audit as scalar
import rr_streams
import rr_run
import rr_worker


def test_stable_effects_noise_and_constant_benefit_counterexamples():
    stable=primary.statistics_of([[1,1,1,1],[-1,-1,-1,-1]],[.5,.5])
    assert stable['variance']==1 and stable['future_noise']==0 and stable['mean_benefit']==0
    homogeneous=primary.statistics_of([[1,1,1,1],[1,1,1,1]],[.25,.75])
    assert homogeneous['variance']==0 and homogeneous['future_noise']==0 and homogeneous['mean_benefit']==1
    noise=primary.statistics_of([[1,-1],[-1,1]],[.5,.5])
    assert noise['variance']==-1 and noise['future_noise']==2
    for d,w in [([[1,-1],[-1,1]],[.5,.5]),([[1,1,1,1],[-1,-1,-1,-1]],[.25,.75])]:
        for key,value in scalar.scalar_statistics(d,w).items():
            assert np.allclose(primary.statistics_of(d,w)[key],value,rtol=0,atol=1e-12)


@pytest.mark.parametrize('probabilities', [([.1,.4,.5],[.3,.6,.1]),([.1,.6,.3],[.1,.6,.3])])
def test_exact_finite_enumeration_unbiased_effect_variance_and_noise(probabilities):
    support=(-1,0,1);weights=(.25,.75)
    means=[sum(p*x for p,x in zip(row,support,strict=True)) for row in probabilities]
    target=sum(w*v*v for w,v in zip(weights,means,strict=True))-sum(w*v for w,v in zip(weights,means,strict=True))**2
    noise=sum(weights[i]*(sum(p*x*x for p,x in zip(probabilities[i],support,strict=True))-means[i]**2) for i in range(2))
    estimates=[];noises=[];masses=[]
    for choices in itertools.product(range(3),repeat=4):
        probability=math.prod(probabilities[i//2][choices[i]] for i in range(4))
        d=[[support[choices[0]],support[choices[1]]],[support[choices[2]],support[choices[3]]]]
        stat=primary.statistics_of(d,weights)
        estimates.append(probability*stat['variance']);noises.append(probability*stat['future_noise']);masses.append(probability)
    assert math.isclose(math.fsum(masses),1,abs_tol=1e-12)
    assert math.isclose(math.fsum(estimates),target,abs_tol=1e-12)
    assert math.isclose(math.fsum(noises),noise,abs_tol=1e-12)


def synthetic_outcomes():
    rows,forecasts,base,_=fixtures.panel()
    outcomes=[]
    for rep in C['cohort']['new_replicates']:
        for index,o in enumerate(base):
            value=dict(o,replicate=rep)
            if rep==1 and index%3==0:
                value['control'],value['repaired']=value['repaired'],value['control']
            outcomes.append(value)
    return rows,forecasts,outcomes


def test_scalar_analysis_class_weights_harms_deletion_and_forecast_costs():
    rows,forecasts,outcomes=synthetic_outcomes()
    result=primary.analyze(rows,forecasts,outcomes)
    assert scalar.evaluate(rows,forecasts,outcomes,result)['status']=='PASS'
    for regime in ('matched','independent'):
        value=result['regimes'][regime]
        assert value['packets'][0]['weight']==.25
        assert value['packets'][1]['weight']==.125
        assert value['events']['harm']['count']>0
        assert [v['block'] for v in value['leave_one_block']]==[-2,-1]
        assert [value['control_forecasts'][m]['extra_native_probes'] for m in ('tt008','direct_rival','candidate')]==[0,8,64]
    forged=copy.deepcopy(result);forged['regimes']['matched']['variance']+=.01
    with pytest.raises(ValueError): scalar.evaluate(rows,forecasts,outcomes,forged)


def test_no_analysis_from_missing_duplicate_or_nonbinary_outcomes():
    rows,forecasts,outcomes=synthetic_outcomes()
    for bad in (outcomes[:-1],outcomes+[outcomes[0]]):
        with pytest.raises(ValueError): primary.analyze(rows,forecasts,bad)
    bad=copy.deepcopy(outcomes);bad[0]['repaired']=2
    with pytest.raises(ValueError): primary.analyze(rows,forecasts,bad)


def test_zero_variance_is_unresolved():
    rows,forecasts,outcomes=synthetic_outcomes()
    for o in outcomes: o['control']=o['repaired']=1
    result=primary.analyze(rows,forecasts,outcomes)
    assert result['signal']=='UNRESOLVED'
    assert scalar.evaluate(rows,forecasts,outcomes,result)['status']=='PASS'
    for regime in ('matched','independent'):
        assert result['regimes'][regime]['primary']['zero_variance_caution']


def test_replicate_stage_seed_separation_and_noise_coupling():
    key=[1,'history',0,0]
    seeds={rr_streams.seed(stage,rep,key,15,'writer',channel) for stage in ('pilot','benchmark','qualification') for rep in range(4) for channel in ('injury','forcing')}
    assert len(seeds)==24
    independent=rr_streams.environment(0,'qualification',key,15,'writer','independent')
    matched=rr_streams.environment(0,'qualification',key,15,'writer','matched')
    assert np.array_equal(independent[0],matched[0]) and matched[0].sum()==24
    assert not np.any(matched[0]&inherited.e.PORTS.any(axis=0))
    for a,b in zip(independent[1:],matched[1:],strict=True):
        assert np.array_equal(a[...,0,:,:],b[...,0,:,:])
        assert np.array_equal(b[...,0,:,:],b[...,1,:,:])
        assert not np.array_equal(a[...,0,:,:],a[...,1,:,:])
    again=rr_streams.environment(0,'qualification',key,15,'writer','independent')
    assert all(np.array_equal(a,b) for a,b in zip(independent,again,strict=True))
    other=rr_streams.environment(1,'qualification',key,15,'writer','independent')
    assert not np.array_equal(independent[2],other[2])


def test_inherited_action_identity_and_module_separation():
    import paired
    import verify
    assert Path(paired.__file__).resolve()==ROOT/'legacy/paired.py'
    assert Path(verify.__file__).resolve()==ROOT/'legacy/verify.py'
    assert Path(scalar.__file__).resolve()==ROOT/'rr_audit.py'
    seal=read(ROOT/'context/02_PANEL_SEAL.json')
    original=ev.load(ROOT/'context/00_ACTIONS.npz',seal['action_arrays_sha256'])['initial_packets']
    indices=[i for i in range(len(original)) if not np.array_equal(original[i,0],original[i,1])]
    assert indices
    i=indices[0]
    prepared,_,_=actions.prepare([seal['rows'][i]],original[i:i+1,0])
    assert prepared.tobytes()==original[i:i+1].tobytes()


def benchmark_receipts(seconds):
    return [dict(stage='benchmark',records=4,batches=2,wall_seconds=seconds,primary_native_reads=304,flat_native_reads=76) for _ in range(4)]


def test_strict_cost_gate_and_complete_concurrent_measurement():
    assert rr_run.price(benchmark_receipts(4),217)['passed']
    assert not rr_run.price(benchmark_receipts(4),216)['passed']
    with pytest.raises(ValueError): rr_run.price(benchmark_receipts(4)[:-1],1000)


def test_failed_cost_gate_cannot_generate_scientific_futures(tmp_path,monkeypatch):
    seen=[]
    monkeypatch.setattr(rr_run,'verify_snapshot',lambda:0)
    monkeypatch.setattr(rr_run,'admission',lambda:dict(within_limit=True))
    original_read=rr_run.read
    monkeypatch.setattr(rr_run,'read',lambda path: {'status':'PASS'} if Path(path).name=='QUALIFICATION.json' else original_read(path))
    monkeypatch.setattr(Guard,'check',lambda self:None)
    def fake_seal(folder,stage,rows,forecasts,packets):
        folder.mkdir();return folder/'PANEL_SEAL.json'
    monkeypatch.setattr(rr_run,'seal_panel',fake_seal)
    def fake_replicates(folder,seal,stage,deadline,processes):
        seen.append(stage);return [],benchmark_receipts(1000)
    monkeypatch.setattr(rr_run,'concurrent_replicates',fake_replicates)
    output=tmp_path/'gate_failed';rr_run.run(output)
    assert seen==['benchmark']
    assert read(output/'COMPLETE.json')['decision']=='BUDGET_GATE_NOT_MET'
    assert not (output/'study').exists() and not (output/'OUTCOMES.json').exists()


def test_worker_failure_is_durable_and_attempt_cannot_overwrite(tmp_path):
    output=tmp_path/'failed'
    with pytest.raises(FileNotFoundError):
        rr_worker.run(output,tmp_path/'missing_seal','unused',0,'qualification',time.time()+20)
    assert read(output/'FAILED.json')['type']=='FileNotFoundError'
    assert read(output/'STATUS.json')['status']=='FAILED'
    with pytest.raises(FileExistsError):
        rr_worker.run(output,tmp_path/'missing_seal','unused',0,'qualification',time.time()+20)


def test_expired_guard_and_worker_cleanup(tmp_path):
    with pytest.raises(TimeoutError): Guard(tmp_path,time.time()-1).check()
    children=[subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)'],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL) for _ in range(2)]
    try:
        rr_run.stop_workers(children)
        assert all(p.poll() is not None for p in children)
    finally:
        for p in children:
            if p.poll() is None:p.kill();p.wait()
