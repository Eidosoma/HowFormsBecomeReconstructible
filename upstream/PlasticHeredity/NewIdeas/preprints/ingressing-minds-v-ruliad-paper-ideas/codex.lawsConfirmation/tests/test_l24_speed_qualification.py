"""D091 short disposable/synthetic tests before full-duration speed outcomes."""
from copy import deepcopy
import inspect
from pathlib import Path

import numpy as np
import pytest

from laws_confirmation import l24_speed_qualification as p

SHORT=p.source.Config(parents=1,draws=2,settle=4,parent_steps=8,zap=6,child_steps=6,times=(0,1,2,3,6))
WINDOW=p.temporal.Window(active=10,pulse=2,recovery=10)


@pytest.fixture(scope='module')
def example():
    old,_=p.source.execute_parent(p.source.context(p.source.DISPOSABLE,SHORT),0,p.source.checker())
    original,_=p.temporal.execute_parent(old,index=p.source.DISPOSABLE,parent=0,cfg=SHORT,window=WINDOW)
    result,meta=p.execute_parent(original,index=p.source.DISPOSABLE,parent=0,cfg=SHORT,window=WINDOW)
    return original,result,meta


def test_fixed_scope_and_counts():
    c=p.contract()
    assert c['writer_rates']==[.0005,.005] and c['rho']==.002 and c['norm']==.3
    assert c['writer_trajectories_evaluated']==8*4*2*3==192
    assert c['new_fast_writer_trajectories']==96 and c['source_writer_anchors_in_count']==96
    assert c['descendant_lives_evaluated']==32*2*2*20*8==20480
    assert c['source_off_anchor_lives_in_count']==10240 and c['source_on_anchor_lives_in_count']==3072
    assert (c['binary_rows'],c['continuous_rows'],c['writer_rows'])==(48,96,24)
    assert c['primary_writer_boundary']==1000 and c['primary_descendant_time']==500
    assert c['fast_rate_outside_original_E70_u_range'] and c['fast_rate_factor']==10
    assert c['protection_arms']==0 and not c['rate_search'] and not c['automatic_followup']
    assert not c['body_feedback'] and not c['parent_body_physics_simulated'] and c['new_full_parent_lives']==0
    assert c['packet_bytes']==2048 and c['inherited_fields']==['theta'] and c['theta_frozen_in_descendant']
    assert not c['fitness_or_semantic_selectivity_claim'] and not c['renewal_or_biological_claim']


def test_independent_writer_packets_aliases(example):
    original,result,meta=example
    assert p.checker().check_writer(original,result,WINDOW)<=1e-12
    assert p.checker().check_packets(original,result,WINDOW)<=1e-12
    assert p.checker().check_aliases(original,result)
    assert meta['writer_max_abs']<=1e-12 and meta['geometry_max_abs']<=1e-12


def test_source_inputs_unchanged(example):
    original,_,_=example;before={k:v.copy() for k,v in original.items()}
    result=p.write_records(original,WINDOW);p.build_packets(result,WINDOW)
    for k,v in before.items(): np.testing.assert_array_equal(original[k],v)


def test_equal_rates_collapse_to_source_aliases(example,monkeypatch):
    original,_,_=example;monkeypatch.setattr(p,'RATES',(.0005,.0005))
    result=p.write_records(original,WINDOW)
    np.testing.assert_array_equal(result['writer_states'][:,:,0],result['writer_states'][:,:,1])


def test_raw_first_update_increments_are_tenfold(example):
    original,result,_=example;ref=result['writer_states'][1,0,0];theta=original['initial_writer'][1]
    slow=.9995*theta+.0005*np.tanh(ref);fast=.995*theta+.005*np.tanh(ref)
    np.testing.assert_allclose(fast-theta,10*(slow-theta),rtol=0,atol=1e-12)
    assert not np.array_equal(result['writer_states'][-1,1,0],result['writer_states'][-1,1,1])


@pytest.mark.parametrize('key',['input_base','input_delta','initial_writer','targets','permutation','schedule','writer_states','writer_trace','proposal_details','R_weights'])
def test_corrupt_writer_detected(example,key):
    original,result,_=deepcopy(example);result[key].flat[-1]+=.01 if key!='permutation' else 1
    with pytest.raises(AssertionError): p.checker().check_writer(original,result,WINDOW)


@pytest.mark.parametrize('key',['records','control_units','reconstructed_written','geometry','geometry_energy_available'])
def test_corrupt_packet_geometry_detected(example,key):
    original,result,_=deepcopy(example)
    if key=='geometry_energy_available': result[key].flat[-1]=not result[key].flat[-1]
    else: result[key].flat[-1]+=.01
    with pytest.raises(AssertionError): p.checker().check_packets(original,result,WINDOW)


def test_degenerate_fast_increment_fails_without_selection(example):
    _,result,_=deepcopy(example)
    for boundary in WINDOW.boundaries:
        states=result['writer_states'][WINDOW.times.index(boundary),1,1];states[1]=states[0]
    with pytest.raises(ValueError): p.build_packets(result,WINDOW)


def test_own_rate_baseline_and_exact_actual_written_records(example):
    _,result,_=example
    for end,boundary in enumerate(WINDOW.boundaries):
        written=result['writer_states'][WINDOW.times.index(boundary),1].reshape(6,16,16)
        np.testing.assert_array_equal(result['records'][10*end:10*end+6],written)
        assert result['geometry'][end,0,1]==0 and result['geometry'][end,3,1]==0
        assert not result['geometry_energy_available'][end,0] and not result['geometry_energy_available'][end,3]
        for arm in (4,5,6,7,8,9):
            actual=np.sqrt(np.mean((result['records'][10*end+arm]-written[3])**2))
            assert abs(actual-result['geometry'][end,arm,1])<1e-12


@pytest.mark.parametrize('reader',[0,1])
def test_independent_child_physics(example,reader):
    _,result,meta=example
    assert p.source.checker().check_descendants(result['descendants'][reader],result['records'],
        p.source.context(p.source.DISPOSABLE,SHORT),0,reader,meta['children'][reader])<=1e-10


@pytest.mark.parametrize('field',range(3))
@pytest.mark.parametrize('onoff,arm',[(1,5),(0,0),(0,1),(0,2),(0,10),(0,11),(0,12)])
def test_corrupt_source_anchors_detected(example,field,onoff,arm):
    original,result,_=deepcopy(example);result['descendants'][0,-1,field,onoff,arm,0,0,0]+=.1
    with pytest.raises(AssertionError): p.checker().check_aliases(original,result)


def test_packet_order_does_not_communicate(example):
    _,result,_=example;order=(19,5,1,0,13,17)
    packets=tuple(p.source.encode(result['records'][i]) for i in order)
    assert all(isinstance(x,bytes) and len(x)==2048 for x in packets)
    raw,_=p.source.descendants(packets,index=p.source.DISPOSABLE,parent=0,reader=0,cfg=SHORT)
    np.testing.assert_array_equal(raw,result['descendants'][0][:,:,:,list(order)])


def test_no_source_parent_life_or_temporal_regeneration(example,monkeypatch):
    def forbidden(*args,**kwargs): raise AssertionError('full source regeneration forbidden')
    for module,name in ((p.source,'parent_life'),(p.source,'execute_parent'),(p.temporal,'write_records'),(p.temporal,'execute_parent')):
        monkeypatch.setattr(module,name,forbidden)
    original,expected,_=example
    actual,_=p.execute_parent(original,index=p.source.DISPOSABLE,parent=0,cfg=SHORT,window=WINDOW)
    np.testing.assert_array_equal(actual['descendants'],expected['descendants'])


def test_no_parent_body_physics(example,monkeypatch):
    original,expected,_=example;api=p.source.api()
    def forbidden(*args,**kwargs): raise AssertionError('parent physics excluded')
    monkeypatch.setattr(p.source,'api',lambda:api|{'blueprint_step':forbidden})
    np.testing.assert_array_equal(p.write_records(original,WINDOW)['writer_states'],expected['writer_states'])


def test_target_labels_do_not_guide_writing(example):
    original,expected,_=deepcopy(example);original['targets']*=-1
    actual=p.write_records(original,WINDOW)
    np.testing.assert_array_equal(actual['writer_states'],expected['writer_states'])


@pytest.fixture(scope='module')
def pool_example():
    rng=np.random.default_rng(9101)
    blocks=[dict(values=rng.normal(size=(2,2,5,2,20,2,3,8)),writer_trace=rng.normal(size=(2,21,2,3,2,3,6)),
        proposal_details=rng.normal(size=(2,20,2,3,3)),geometry=rng.normal(size=(2,2,10,6)),R_weights=rng.normal(size=(2,21,3))) for _ in range(8)]
    return blocks,*p.summarize(blocks,WINDOW)


def test_full_pool_and_qualification_independently_checked(pool_example):
    assert p.checker().check_summary(*pool_example,WINDOW)
    rows=pool_example[2];assert p.checker().check_qualification(rows,p.qualification(rows,WINDOW),WINDOW)


@pytest.mark.parametrize('row',range(168))
def test_every_registered_summary_row_checked(pool_example,row):
    data=deepcopy(pool_example);group,position=(2,row) if row<144 else (3,row-144)
    data[group][position]['mean']+=.1
    with pytest.raises(AssertionError): p.checker().check_summary(*data,WINDOW)


@pytest.mark.parametrize('key',['pointwise_block_bootstrap_95','block_means','parent_means','positive','tied','negative','paired_positive','paired_tied','paired_negative','minimum','maximum'])
def test_intervals_units_counts_and_ranges_checked(pool_example,key):
    data=deepcopy(pool_example);row=data[2][0]
    if key=='parent_means': row[key][0][0]+=.1
    elif isinstance(row[key],list): row[key][0]+=.1
    else: row[key]+=.1
    with pytest.raises(AssertionError): p.checker().check_summary(*data,WINDOW)


@pytest.mark.parametrize('key',['means','writer_means','proposal_details_means','geometry_means','R_weights_means'])
def test_all_pooled_arrays_checked(pool_example,key):
    data=deepcopy(pool_example);data[1][key].flat[-1]+=.1
    with pytest.raises(AssertionError): p.checker().check_summary(*data,WINDOW)


@pytest.mark.parametrize('criterion',range(32))
def test_every_qualification_criterion_checked(pool_example,criterion):
    rows=pool_example[2];result=p.qualification(rows,WINDOW);group,position=divmod(criterion,16)
    result[group]['criteria'][position]['passed']=not result[group]['criteria'][position]['passed']
    with pytest.raises(AssertionError): p.checker().check_qualification(rows,result,WINDOW)


def test_qualification_needs_every_criterion_and_both_boundaries_separate(pool_example):
    rows=deepcopy(pool_example[2])
    for row in rows:
        row.update(positive=8,block_means=[1.]*8,pointwise_block_bootstrap_95=[.5,1.5])
    result=p.qualification(rows,WINDOW)
    assert all(r['stronger_readable_channel_qualified'] for r in result)
    target=next(r for r in rows if r['boundary']==WINDOW.total and r['reader']=='native_T' and r['metric']=='damage_fidelity' and r['label']=='fast_late_pulse_minus_shuffled')
    target['positive']=7;target['block_means'][0]=0
    result=p.qualification(rows,WINDOW)
    assert result[0]['stronger_readable_channel_qualified'] and not result[0]['primary']
    assert not result[1]['stronger_readable_channel_qualified'] and result[1]['primary']
    assert p.checker().check_qualification(rows,result,WINDOW)
    target['positive']=8;target['block_means'][0]=1;target['pointwise_block_bootstrap_95'][0]=0
    assert not p.qualification(rows,WINDOW)[1]['stronger_readable_channel_qualified']


def test_differences_adjust_for_each_rates_baseline():
    values=np.array([1,3,2,10,12,11],float)
    assert p.checker().contrasts(values)[4]==p.checker().contrasts(values)[5]==0
    assert p.previous.difference(values,p.CONTRASTS[4][1],0)==0


def test_external_saved_roundtrip(example,tmp_path):
    _,result,_=example;path=tmp_path/'panel.npz';p.source.base.atomic_npz(path,result,tmp_path)
    with np.load(path,allow_pickle=False) as saved:
        assert set(saved.files)==set(result)
        for key,value in result.items(): np.testing.assert_array_equal(saved[key],value)
    assert '/mnt/bioIce1/' in str(path)


def test_resource_detachment_and_read_only_audit():
    code=inspect.getsource(p.detach)
    for forbidden in ('child.poll(', 'child.wait(', 'time.sleep(', 'while '): assert forbidden not in code
    assert 'start_new_session=True' in code and 'subprocess.DEVNULL' in code
    assert 'max_workers=WORKERS' in inspect.getsource(p.run_experiment) and 'must_detach' in inspect.getsource(p.run_experiment)
    audit=inspect.getsource(p.audit_saved)
    for forbidden in ('check_writer(', 'check_descendants(', 'write_records(', 'atomic_text(', 'strict_json(', 'atomic_npz('): assert forbidden not in audit
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
