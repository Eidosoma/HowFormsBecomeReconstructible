"""D090 short disposable/synthetic checks; no new full-duration main outcomes."""
from copy import deepcopy
import inspect
from pathlib import Path

import numpy as np
import pytest

from laws_confirmation import l24_recovery_reference as p

SHORT=p.source.Config(parents=1,draws=2,settle=4,parent_steps=8,zap=6,child_steps=6,times=(0,1,2,3,6))
WINDOW=p.previous.Window(active=10,pulse=2,recovery=10)


@pytest.fixture(scope='module')
def example():
    d086,_=p.source.execute_parent(p.source.context(p.source.DISPOSABLE,SHORT),0,p.source.checker())
    original,_=p.previous.execute_parent(d086,index=p.source.DISPOSABLE,parent=0,cfg=SHORT,window=WINDOW)
    result,meta=p.execute_parent(original,index=p.source.DISPOSABLE,parent=0,cfg=SHORT,window=WINDOW)
    return original,result,meta


def test_fixed_contract_scope():
    c=p.contract()
    assert c['rho']==.002 and c['writer_rate']==.0005 and c['norm']==.3
    assert c['recovery_times']==[0,1,50,250,500] and c['absolute_writer_times']==[500,501,550,750,1000]
    assert c['descendant_lives_evaluated']==8*4*2*2*11*8==11264
    assert c['writer_recovery_trajectories_evaluated']==8*4*11==352
    assert c['unique_writer_trajectories']==288 and c['new_intervention_trajectories']==192
    assert c['source_on_anchor_or_rescue_lives_in_count']==32*2*5*8==2560
    assert c['source_off_anchor_lives_in_count']==5632
    assert (c['binary_rows'],c['continuous_rows'],c['writer_rows'],c['growth_rows'])==(32,64,48,8)
    assert c['packet_bytes']==2048 and c['inherited_fields']==['theta']
    assert not c['body_feedback'] and not c['parent_body_physics_simulated'] and c['new_full_parent_lives']==0
    assert not c['fitness_or_semantic_selectivity_claim'] and not c['renewal_or_biological_claim']
    assert c['scientific_pass_gate'] is None and not c['automatic_followup']
    assert not c['rescue_is_independent_evidence'] and not c['reverse_R_norm_matched']


def test_independent_writer_packets_and_aliases(example):
    original,result,meta=example
    assert p.checker().check_writer(original,result,WINDOW)<=1e-12
    assert p.checker().check_packets(original,result) and p.checker().check_aliases(original,result)
    assert meta['writer_max_abs']<=1e-12


def test_only_declared_half_swapped_and_source_preserved(example):
    original,result,_=example;before={k:v.copy() for k,v in original.items()}
    actual=p.recover(original,WINDOW)
    for k,v in before.items(): np.testing.assert_array_equal(original[k],v)
    np.testing.assert_array_equal(actual['initial_writer'],result['initial_writer'])
    state=result['initial_writer'];onset=result['onset']
    assert np.any(onset[0,0])  # Baseline reference is not a zero-reset control.
    for start,history in ((1,1),(6,2)):
        np.testing.assert_array_equal(state[1,start+1],onset[1,history])
        np.testing.assert_array_equal(state[0,start+1],onset[0,0])
        np.testing.assert_array_equal(state[0,start+2],onset[0,history])
        np.testing.assert_array_equal(state[1,start+2],onset[1,0])
        np.testing.assert_allclose(state[0,start+3]-onset[0,0],-(onset[0,history]-onset[0,0]),rtol=0,atol=1e-12)
        np.testing.assert_array_equal(state[:,start+4],state[:,start])


@pytest.mark.parametrize('key',['input_base','targets','onset','initial_writer','restore_intermediate_R','writer_states','writer_trace','proposal_details'])
def test_corrupt_intervention_or_recurrence_detected(example,key):
    original,result,_=deepcopy(example);result[key].flat[-1]+=.01
    with pytest.raises(AssertionError): p.checker().check_writer(original,result,WINDOW)


def test_packet_corruption_detected(example):
    original,result,_=deepcopy(example);result['records'][2,0,0]+=.01
    with pytest.raises(AssertionError): p.checker().check_packets(original,result)


@pytest.mark.parametrize('arm',[0,1,2,5,6,7,10])
def test_corrupt_alias_or_reset_R_detected(example,arm):
    original,result,_=deepcopy(example);result['writer_states'][-1,0,arm,0,0]+=.01
    with pytest.raises(AssertionError): p.checker().check_writer(original,result,WINDOW)


@pytest.mark.parametrize('reader',[0,1])
def test_independent_descendant_physics(example,reader):
    _,result,meta=example
    assert p.source.checker().check_descendants(result['descendants'][reader],result['records'],
        p.source.context(p.source.DISPOSABLE,SHORT),0,reader,meta['children'][reader])<=1e-10


@pytest.mark.parametrize('field',range(3))
@pytest.mark.parametrize('onoff,arm',[(1,2),(0,1),(0,5),(0,6),(0,10)])
def test_corrupt_off_on_or_rescue_anchors_detected(example,field,onoff,arm):
    original,result,_=deepcopy(example);result['descendants'][0,-1,field,onoff,arm,0,0,0]+=.1
    with pytest.raises(AssertionError): p.checker().check_aliases(original,result)


def test_reordered_packets_are_isolated(example):
    _,result,_=example;order=(10,7,2,0,6,1)
    packets=tuple(p.source.encode(result['records'][i]) for i in order)
    assert all(isinstance(x,bytes) and len(x)==2048 for x in packets)
    raw,_=p.source.descendants(packets,index=p.source.DISPOSABLE,parent=0,reader=0,cfg=SHORT)
    np.testing.assert_array_equal(raw,result['descendants'][0][:,:,:,list(order)])


def test_no_parent_or_exposure_regeneration(example,monkeypatch):
    def forbidden(*args,**kwargs): raise AssertionError('source regeneration forbidden')
    for module,name in ((p.source,'parent_life'),(p.source,'execute_parent'),(p.previous,'write_records'),(p.previous,'execute_parent')):
        monkeypatch.setattr(module,name,forbidden)
    original,expected,_=example
    actual,_=p.execute_parent(original,index=p.source.DISPOSABLE,parent=0,cfg=SHORT,window=WINDOW)
    np.testing.assert_array_equal(actual['descendants'],expected['descendants'])


def test_recovery_never_calls_parent_body_physics(example,monkeypatch):
    original,expected,_=example;api=p.source.api()
    def forbidden(*args,**kwargs): raise AssertionError('parent physical feedback forbidden')
    monkeypatch.setattr(p.source,'api',lambda:api|{'blueprint_step':forbidden})
    np.testing.assert_array_equal(p.recover(original,WINDOW)['writer_states'],expected['writer_states'])


def test_targets_observe_but_never_guide_writing(example):
    original,expected,_=deepcopy(example);original['targets']*=-1
    actual=p.recover(original,WINDOW)
    np.testing.assert_array_equal(actual['writer_states'],expected['writer_states'])
    np.testing.assert_array_equal(actual['records'],expected['records'])


@pytest.fixture(scope='module')
def pool_example():
    rng=np.random.default_rng(9001)
    blocks=[dict(values=rng.normal(size=(2,2,5,2,11,2,3,8)),writer_trace=rng.normal(size=(2,4,11,2,3,6)),
        proposal_details=rng.normal(size=(2,3,11,3))) for _ in range(8)]
    return blocks,*p.summarize(blocks)


def test_complete_pool_independently_checked(pool_example):
    assert p.checker().check_summary(*pool_example)


@pytest.mark.parametrize('group,count',[(2,96),(3,48),(4,8)])
def test_exact_row_counts(pool_example,group,count):
    assert len(pool_example[group])==count


@pytest.mark.parametrize('row',range(152))
def test_every_summary_row_checked(pool_example,row):
    data=deepcopy(pool_example)
    group,position=(2,row) if row<96 else ((3,row-96) if row<144 else (4,row-144))
    data[group][position]['mean']+=.1
    with pytest.raises(AssertionError): p.checker().check_summary(*data)


@pytest.mark.parametrize('key',['pointwise_block_bootstrap_95','block_means','parent_means','positive','tied','negative','paired_positive','paired_tied','paired_negative','minimum','maximum'])
def test_intervals_units_counts_and_ranges_checked(pool_example,key):
    data=deepcopy(pool_example);row=data[2][0]
    if key=='parent_means': row[key][0][0]+=.1
    elif isinstance(row[key],list): row[key][0]+=.1
    else: row[key]+=.1
    with pytest.raises(AssertionError): p.checker().check_summary(*data)


@pytest.mark.parametrize('key',['means','writer_means','proposal_details_means'])
def test_all_pooled_arrays_checked(pool_example,key):
    data=deepcopy(pool_example);data[1][key].flat[-1]+=.1
    with pytest.raises(AssertionError): p.checker().check_summary(*data)


def test_factorial_interaction_not_assumed_zero():
    v=np.zeros(11);v[1:4]=[8,3,2]
    assert p.checker().contrasts(v,1)[5]==3
    assert p.difference(v,p.CONTRASTS[5][1],0)==3


def test_saved_external_roundtrip(example,tmp_path):
    _,result,_=example;path=tmp_path/'panel.npz';p.source.base.atomic_npz(path,result,tmp_path)
    with np.load(path,allow_pickle=False) as saved:
        assert set(saved.files)==set(result)
        for key,value in result.items(): np.testing.assert_array_equal(saved[key],value)
    assert '/mnt/bioIce1/' in str(path)


def test_resource_detachment_and_read_only_audit():
    code=inspect.getsource(p.detach)
    for forbidden in ('child.poll(', 'child.wait(', 'time.sleep(', 'while '): assert forbidden not in code
    assert 'start_new_session=True' in code and 'subprocess.DEVNULL' in code
    assert 'max_workers=WORKERS' in inspect.getsource(p.run_experiment)
    assert 'must_detach' in inspect.getsource(p.run_experiment)
    audit=inspect.getsource(p.audit_saved)
    for forbidden in ('check_writer(', 'check_descendants(', 'recover(', 'atomic_text(', 'strict_json(', 'atomic_npz('): assert forbidden not in audit
    launcher=Path(p.__file__).resolve().parents[2]/p.SCIENCE[3]
    assert 'taskset -c 0-3' in launcher.read_text() and 'PYTHONDONTWRITEBYTECODE=1' in launcher.read_text()


def test_immutable_inputs_and_no_retry(monkeypatch,tmp_path):
    from laws_confirmation.io import atomic_text
    path=tmp_path/'source.txt';atomic_text(path,'initial',tmp_path)
    monkeypatch.setattr(p,'input_paths',lambda root:[path]);monkeypatch.setattr(p,'source_verified',lambda *args:True)
    record=dict(contract=p.contract(),new_full_duration_outcomes_seen=False,input_sha256={str(path):p.sha256_file(path)})
    p.source.strict_json(p.freeze_path(tmp_path),record,tmp_path)
    assert p.frozen_inputs(tmp_path)==record['input_sha256']
    atomic_text(path,'changed',tmp_path)
    with pytest.raises(AssertionError): p.frozen_inputs(tmp_path)
    (tmp_path/'runs'/p.RUN_ID).mkdir(parents=True)
    with pytest.raises(FileExistsError): p.prepare(tmp_path)


@pytest.mark.parametrize('key',[None,'contract_sha256','projected_seconds','must_detach','effects_not_reported','freeze_sha256'])
def test_timing_and_freeze_guards(tmp_path,key):
    from laws_confirmation.io import atomic_text
    atomic_text(p.freeze_path(tmp_path),'frozen',tmp_path)
    files={str(tmp_path/'tmp'/f'{p.RUN_ID}_benchmark'/name):'' for name in ('panel.npz','verification.json')}
    for name in files: atomic_text(Path(name),'retained',tmp_path)
    files={name:p.sha256_file(Path(name)) for name in files}
    timing=dict(run_id=p.RUN_ID,passed=True,disposable=p.source.DISPOSABLE,contract_sha256=p.canonical_digest(p.contract()),
        parent_seconds=25.,hash_seconds=1.,projected_seconds=982.,must_detach=True,forecast_does_not_credit_parallel_speedup=True,
        effects_not_reported=True,input_sha256={},freeze_sha256=p.sha256_file(p.freeze_path(tmp_path)),benchmark_files=files)
    if key is None: assert p.validate_timing(tmp_path,timing,{});return
    timing[key]=False if key in ('must_detach','effects_not_reported') else 'corrupt'
    with pytest.raises(AssertionError): p.validate_timing(tmp_path,timing,{})
