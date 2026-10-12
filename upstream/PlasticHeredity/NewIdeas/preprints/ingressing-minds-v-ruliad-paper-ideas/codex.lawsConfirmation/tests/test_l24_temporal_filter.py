"""D089 short disposable and synthetic checks, before full-duration outcomes."""
from copy import deepcopy
import inspect
from pathlib import Path

import numpy as np
import pytest

from laws_confirmation import l24_temporal_filter as p

SHORT=p.source.Config(parents=1,draws=2,settle=4,parent_steps=8,zap=6,child_steps=6,times=(0,1,2,3,6))
WINDOW=p.Window(active=10,pulse=2,recovery=10)


@pytest.fixture(scope='module')
def example():
    original,_=p.source.execute_parent(p.source.context(p.source.DISPOSABLE,SHORT),0,p.source.checker())
    result,meta=p.execute_parent(original,index=p.source.DISPOSABLE,parent=0,cfg=SHORT,window=WINDOW)
    return original,result,meta


def test_fixed_scope_and_counts():
    c=p.contract()
    assert c['writer_rate']==.0005 and c['rho']==.002 and c['norm']==.3
    assert c['descendant_lives_evaluated']==8*4*2*2*20*8==20480
    assert c['new_counterfactual_writer_trajectories']==8*4*5==160
    assert c['binary_rows']==20 and c['continuous_rows']==40 and c['writer_rows']==12
    assert not c['body_feedback'] and not c['parent_body_physics_simulated'] and c['new_full_parent_lives']==0
    assert c['primary_writer_boundary']==1000 and c['primary_descendant_time']==500
    assert c['utility_is_engineer_declared'] and not c['fitness_or_semantic_selectivity_claim']
    assert c['scientific_pass_gate'] is None and not c['automatic_followup']
    assert c['packet_bytes']==2048 and c['inherited_fields']==['theta']


@pytest.mark.parametrize('values',[(3,1,2),(10,5,10),(10,0,10),(10,2,2)])
def test_invalid_clocks_fail(values):
    with pytest.raises(ValueError): p.Window(*values)


def test_schedule_peak_signed_dose_and_recovery():
    a=p.schedule()
    np.testing.assert_allclose(a.sum(axis=0),[0,500,50,50,50],rtol=0,atol=1e-12)
    np.testing.assert_allclose((a*a).sum(axis=0),[0,500,50,50,5],rtol=0,atol=1e-12)
    np.testing.assert_array_equal(a[:500,1],np.ones(500))
    assert not a[500:].any() and not a[50:,2].any() and not a[:450,3].any()
    assert not p.contract()['squared_integrated_input_matched_for_dose_control']


def test_independent_writer_geometry_alias_checks(example):
    original,result,meta=example
    assert p.checker().check_writer(original,result,WINDOW)<=1e-12
    assert p.checker().check_packets(result,WINDOW)<=1e-12
    assert p.checker().check_aliases(original,result)
    assert meta['writer_max_abs']<=1e-12


def test_original_inputs_unchanged(example):
    original,_,_=example;before={k:v.copy() for k,v in original.items()}
    result=p.write_records(original,WINDOW);p.build_packets(result,WINDOW)
    for k,v in before.items(): np.testing.assert_array_equal(original[k],v)


def test_production_advance_bridges_original_one_step(example):
    original,_,_=example;x=original['parent_states']
    ref,theta,_=p.advance(x[:,4,2],x[:,4,3],x[:,5,0],p.source.api()['project_theta'])
    np.testing.assert_array_equal(ref,x[:,5,2]);np.testing.assert_array_equal(theta,x[:,5,3])


@pytest.mark.parametrize('key',['input_base','input_delta','initial_writer','schedule','writer_states','writer_trace','proposal_details','R_weights','targets','permutation'])
def test_corrupt_writer_inputs_states_or_observers_detected(example,key):
    original,result,_=deepcopy(example);result[key].flat[-1]+=1
    with pytest.raises(AssertionError): p.checker().check_writer(original,result,WINDOW)


@pytest.mark.parametrize('key',['records','control_units','reconstructed_written','geometry','geometry_energy_available'])
def test_corrupt_packet_or_geometry_detected(example,key):
    _,result,_=deepcopy(example)
    if key=='geometry_energy_available': result[key].flat[-1]=not result[key].flat[-1]
    else: result[key].flat[-1]+=.01
    with pytest.raises(AssertionError): p.checker().check_packets(result,WINDOW)


def test_degenerate_written_increment_fails_without_fallback(example):
    _,result,_=deepcopy(example)
    for tick in WINDOW.boundaries:
        states=result['writer_states'][WINDOW.times.index(tick),1];states[1]=states[0]
    with pytest.raises(ValueError): p.build_packets(result,WINDOW)


def test_actual_baselines_and_initial_record_not_replaced(example):
    original,result,_=example;records=result['records'].reshape(2,10,16,16)
    for end,t in enumerate(WINDOW.boundaries):
        np.testing.assert_array_equal(records[end,:5],result['writer_states'][WINDOW.times.index(t),1])
        np.testing.assert_array_equal(records[end,9],original['parent_states'][0,3,3])
    assert all(len(p.source.encode(x))==2048 for x in result['records'])


@pytest.mark.parametrize('reader',[0,1])
def test_independent_descendant_physics(example,reader):
    _,result,meta=example
    assert p.source.checker().check_descendants(result['descendants'][reader],result['records'],
        p.source.context(p.source.DISPOSABLE,SHORT),0,reader,meta['children'][reader])<=1e-10


@pytest.mark.parametrize('field',range(3))
def test_corrupt_off_anchor_detected(example,field):
    original,result,_=deepcopy(example);result['descendants'][0,-1,field,1,7,0,0,0]+=.1
    with pytest.raises(AssertionError): p.checker().check_aliases(original,result)


def test_flattened_boundaries_do_not_communicate(example):
    _,result,_=example;order=(19,0,13,3,5,11)
    raw,_=p.source.descendants(tuple(p.source.encode(result['records'][i]) for i in order),
        index=p.source.DISPOSABLE,parent=0,reader=0,cfg=SHORT)
    np.testing.assert_array_equal(raw,result['descendants'][0][:,:,:,list(order)])


def test_production_does_not_regenerate_full_parents(example,monkeypatch):
    def forbidden(*args,**kwargs): raise AssertionError('full parent regeneration forbidden')
    monkeypatch.setattr(p.source,'parent_life',forbidden);monkeypatch.setattr(p.source,'execute_parent',forbidden)
    original,expected,_=example
    actual,_=p.execute_parent(original,index=p.source.DISPOSABLE,parent=0,cfg=SHORT,window=WINDOW)
    np.testing.assert_array_equal(actual['descendants'],expected['descendants'])


def test_writer_clamp_does_not_call_parent_body_physics(example,monkeypatch):
    original,expected,_=example;api=p.source.api()
    def forbidden(*args,**kwargs): raise AssertionError('parent body physics excluded by input clamp')
    monkeypatch.setattr(p.source,'api',lambda:api|{'blueprint_step':forbidden})
    actual=p.write_records(original,WINDOW)
    np.testing.assert_array_equal(actual['writer_states'],expected['writer_states'])


@pytest.fixture(scope='module')
def pool_example():
    rng=np.random.default_rng(8901)
    blocks=[dict(values=rng.normal(size=(2,2,5,2,20,2,3,8)),writer_trace=rng.normal(size=(2,4,5,2,3,6)),
        proposal_details=rng.normal(size=(2,3,5,3)),geometry=rng.normal(size=(2,2,10,6)),R_weights=rng.normal(size=(2,4,5))) for _ in range(8)]
    return blocks,*p.summarize(blocks)


def test_complete_pool_independently_checked(pool_example):
    assert p.checker().check_summary(*pool_example)


@pytest.mark.parametrize('row',range(60))
def test_every_descendant_summary_row_is_checked(pool_example,row):
    blocks,summary,rows,writers=deepcopy(pool_example);rows[row]['mean']+=.1
    with pytest.raises(AssertionError): p.checker().check_summary(blocks,summary,rows,writers)


@pytest.mark.parametrize('row',range(12))
def test_every_writer_summary_row_is_checked(pool_example,row):
    blocks,summary,rows,writers=deepcopy(pool_example);writers[row]['mean']+=.1
    with pytest.raises(AssertionError): p.checker().check_summary(blocks,summary,rows,writers)


@pytest.mark.parametrize('key',['pointwise_block_bootstrap_95','block_means','parent_means'])
def test_intervals_and_unit_values_checked(pool_example,key):
    blocks,summary,rows,writers=deepcopy(pool_example)
    if key=='parent_means': rows[0][key][0][0]+=.1
    else: rows[0][key][0]+=.1
    with pytest.raises(AssertionError): p.checker().check_summary(blocks,summary,rows,writers)


@pytest.mark.parametrize('key',['positive','tied','negative','paired_positive','paired_tied','paired_negative'])
def test_counts_checked(pool_example,key):
    blocks,summary,rows,writers=deepcopy(pool_example);rows[0][key]+=1
    with pytest.raises(AssertionError): p.checker().check_summary(blocks,summary,rows,writers)


@pytest.mark.parametrize('key',['means','writer_means','proposal_details_means','geometry_means','R_weights_means'])
def test_all_pooled_arrays_checked(pool_example,key):
    blocks,summary,rows,writers=deepcopy(pool_example);summary[key].flat[0]+=.1
    with pytest.raises(AssertionError): p.checker().check_summary(blocks,summary,rows,writers)


def test_external_saved_roundtrip(example,tmp_path):
    _,result,_=example;path=tmp_path/'panel.npz';p.source.base.atomic_npz(path,result,tmp_path)
    with np.load(path,allow_pickle=False) as saved:
        for key,value in result.items(): np.testing.assert_array_equal(saved[key],value)
    assert '/mnt/bioIce1/' in str(path)


def test_resources_detachment_and_no_polling():
    code=inspect.getsource(p.detach)
    for forbidden in ('child.poll(', 'child.wait(', 'time.sleep(', 'while '): assert forbidden not in code
    assert 'start_new_session=True' in code and 'subprocess.DEVNULL' in code
    assert 'max_workers=WORKERS' in inspect.getsource(p.run_experiment)
    assert 'must_detach' in inspect.getsource(p.run_experiment)
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
