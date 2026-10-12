"""Synthetic algebra/corruption tests; no new D086 trace outcomes or dynamics."""
from copy import deepcopy
import inspect
from pathlib import Path

import numpy as np
import pytest

from laws_confirmation import l24_signal_chain as audit


def project(x):
    q=x-x.mean(axis=(-2,-1),keepdims=True)
    return q*(.3/np.maximum(q.std(axis=(-2,-1),keepdims=True),1e-9))


@pytest.fixture(scope='module')
def example():
    random=np.random.default_rng(8701)
    raw=np.empty((2,7,4,16,16))
    common=random.normal(0,.4,(4,16,16));common[3]=project(common[3])
    raw[:]=common
    raw[1,4,0,:,12:]*=-1;raw[1,4,1]=raw[1,4,0]
    raw[:,5,0]=.8*raw[:,4,0]
    raw[:,5,1]=.9*raw[:,4,1]+.1*raw[:,5,0]
    raw[:,5,2]=raw[:,4,2]+.002*(raw[:,5,0]-raw[:,4,2])
    raw[:,5,3]=project(.9995*raw[:,4,3]+.0005*np.tanh(raw[:,5,2]))
    raw[:,6,0]=.7*raw[:,5,0];raw[:,6,2]=.9*raw[:,5,2]+.1*raw[:,6,0]
    raw[:,6,3]=project(.99*raw[:,5,3]+.01*np.tanh(raw[:,6,2]))
    good=np.where(raw[0,3,0]>0,1.,-1.);bad=good.copy();bad[:,12:]*=-1
    records=np.stack((raw[0,6,3],raw[1,6,3],np.zeros((16,16)),common[3],project(good),project(bad),project(-bad),project(-good)))
    payload=dict(parent_states=raw,targets=np.stack((good,bad)),records=records,
                 values=random.uniform(size=(2,5,2,8,2,3,8)))
    return payload,audit.analyze_parent(payload)


def test_contract_is_saved_state_only():
    contract=audit.contract()
    assert contract['decision']=='D087' and contract['source_run']==audit.source.RUN_ID
    assert contract['new_simulation_lives']==contract['historical_dynamics_replays']==contract['intermediate_steps_imputed']==0
    assert contract['scientific_pass_gate'] is None and not contract['automatic_followup']
    assert not contract['toy_clock_is_actual_life_model'] and not contract['actual_weak_signal_readout_calibrated']
    assert (contract['rho'],contract['writer_rate'],contract['norm'],contract['window'])==(.002,.0005,.3,50)
    assert len(audit.LABELS)==14 and len(audit.TERMS)==11 and contract['workers']==1


def test_independent_first_step_and_all_observers(example):
    assert audit.checker().check_parent(*example)<=1e-12


@pytest.mark.parametrize('term',range(11))
def test_first_step_term_corruption_detected(example,term):
    payload,result=deepcopy(example);result['terms'][term,1,1]+=.001
    with pytest.raises(AssertionError): audit.checker().check_parent(payload,result)


@pytest.mark.parametrize('metric',range(9))
def test_trace_metric_corruption_detected(example,metric):
    payload,result=deepcopy(example);result['trace'][6,2,0,metric]+=.001
    with pytest.raises(AssertionError): audit.checker().check_parent(payload,result)


@pytest.mark.parametrize('column',range(14))
def test_focal_corruption_detected(example,column):
    payload,result=deepcopy(example);result['focal'][column]+=.001
    with pytest.raises(AssertionError): audit.checker().check_parent(payload,result)


@pytest.mark.parametrize('key',['projection_details','child_contrast'])
def test_other_saved_quantities_checked(example,key):
    payload,result=deepcopy(example);result[key].flat[0]+=.001
    with pytest.raises(AssertionError): audit.checker().check_parent(payload,result)


def test_source_state_clock_corruption_detected(example):
    payload,_=deepcopy(example);payload['parent_states'][1,5,2,0,0]+=.1
    result=audit.analyze_parent(payload)
    with pytest.raises(AssertionError): audit.checker().check_parent(payload,result)


def test_zero_inputs_keep_undefined_ratios_explicit(example):
    payload,_=deepcopy(example)
    for value in payload.values(): value[:]=0
    result=audit.analyze_parent(payload)
    assert np.isfinite(result['focal']).all() and np.isfinite(result['terms']).all()
    assert not result['valid'][9:].any() and result['valid'][:9].all()
    assert audit.checker().check_parent(payload,result)<=1e-12
    block={k:v[None] for k,v in result.items()}
    summary,rows=audit.summarize([block]*8)
    assert not rows[9]['available'] and rows[9]['mean'] is None
    assert rows[9]['valid_parents_per_block']==[0]*8
    assert audit.checker().check_summary([block]*8,summary,rows)


def test_first_step_zero_centering_and_projection_formula(example):
    payload,result=example
    close=np.testing.assert_allclose
    close(result['terms'][2],.002*result['terms'][1],rtol=0,atol=1e-12)
    close(result['terms'][4],.0005*result['terms'][3],rtol=0,atol=1e-12)
    close(result['terms'][6]+result['terms'][7],result['terms'][8],rtol=0,atol=1e-12)
    assert result['focal'][10]<=1+1e-12 and result['focal'][11]<=1+1e-12


def test_no_new_physical_steps_are_called(example,monkeypatch):
    def forbidden(*args,**kwargs): raise AssertionError('new physical evolution is forbidden')
    for name in ('parent_life','descendants','execute_parent','execute_block'):
        monkeypatch.setattr(audit.source,name,forbidden)
    payload,_=example
    assert audit.checker().check_parent(payload,audit.analyze_parent(payload))<=1e-12
    for fn in (audit.analyze_parent,audit.first_step,audit.run_audit):
        text=inspect.getsource(fn)
        assert 'blueprint_step(' not in text and 'life_fitness(' not in text


@pytest.fixture(scope='module')
def pooled(example):
    _,result=example
    blocks=[]
    for block in range(8):
        item={k:np.stack([v,v,v,v]) for k,v in result.items()}
        item['focal']=item['focal']*(1+.01*block)
        blocks.append(item)
    return blocks,*audit.summarize(blocks)


def test_independent_pool_and_bootstrap(pooled):
    assert audit.checker().check_summary(*pooled)


@pytest.mark.parametrize('row',range(14))
def test_every_pooled_column_checked(pooled,row):
    blocks,summary,rows=deepcopy(pooled);rows[row]['mean']+=.1
    with pytest.raises(AssertionError): audit.checker().check_summary(blocks,summary,rows)


@pytest.mark.parametrize('key',['pointwise_block_bootstrap_95','observed_block_range','block_means'])
def test_interval_corruption_checked(pooled,key):
    blocks,summary,rows=deepcopy(pooled);rows[0][key][0]+=.01
    with pytest.raises(AssertionError): audit.checker().check_summary(blocks,summary,rows)


def test_no_silent_drop_of_invalid_ratio(pooled):
    blocks,_,_=deepcopy(pooled);blocks[2]['valid'][1,12]=False
    summary,rows=audit.summarize(blocks)
    assert rows[12]['valid_parents_per_block']==[4,4,3,4,4,4,4,4]
    assert rows[12]['mean'] is None and not rows[12]['available']
    assert audit.checker().check_summary(blocks,summary,rows)


def test_clock_identity_is_checked_independently():
    rows=audit.clock_reference();assert audit.checker().check_clock(rows)
    np.testing.assert_allclose(rows[0]['theta_cascade_unit_step_weight'],1e-6,rtol=0,atol=1e-15)
    assert rows[1]['theta_cascade_unit_step_weight']<rows[1]['theta_direct_unit_step_weight']
    rows[1]['theta_cascade_unit_step_weight']+=.001
    with pytest.raises(AssertionError): audit.checker().check_clock(rows)


def test_exact_weighted_reference_identity_without_futures():
    # Arbitrary fixed scalar input sequence; verifies the EMA algebra only.
    drive=np.linspace(-1,2,50);reference=0.
    for value in drive: reference=.998*reference+.002*value
    recovered=reference/(1-.998**50)
    weights=.002*.998**np.arange(49,-1,-1)
    np.testing.assert_allclose(recovered,np.dot(weights,drive)/sum(weights),rtol=0,atol=1e-12)


def test_roundtrip_external_only(example,tmp_path):
    _,result=example;path=tmp_path/'trace.npz'
    audit.source.base.atomic_npz(path,result,tmp_path)
    with np.load(path,allow_pickle=False) as saved:
        for key,value in result.items(): np.testing.assert_array_equal(saved[key],value)
    assert '/mnt/bioIce1/' in str(path)


def test_frozen_change_and_existing_run_guards(tmp_path,monkeypatch):
    from laws_confirmation.io import atomic_text
    path=tmp_path/'input.txt';atomic_text(path,'initial',tmp_path)
    monkeypatch.setattr(audit,'input_paths',lambda root:[path])
    class Check:
        def source_manifest_check(self,*args): return True
    monkeypatch.setattr(audit,'checker',lambda:Check())
    record=dict(contract=audit.contract(),input_sha256={str(path):audit.sha256_file(path)})
    audit.source.strict_json(audit.freeze_path(tmp_path),record,tmp_path)
    assert audit.verify_freeze(tmp_path)==record['input_sha256']
    atomic_text(path,'changed',tmp_path)
    with pytest.raises(AssertionError): audit.verify_freeze(tmp_path)
    (tmp_path/'runs'/audit.RUN_ID).mkdir(parents=True)
    with pytest.raises(FileExistsError): audit.run_audit(tmp_path)


def test_launcher_resource_caps():
    path=Path(audit.__file__).resolve().parents[2]/audit.SCIENCE[3]
    text=path.read_text()
    assert 'taskset -c 0-3' in text and 'PYTHONDONTWRITEBYTECODE=1' in text
    assert '/mnt/bioIce1/' in text and 'OMP_NUM_THREADS=1' in text
