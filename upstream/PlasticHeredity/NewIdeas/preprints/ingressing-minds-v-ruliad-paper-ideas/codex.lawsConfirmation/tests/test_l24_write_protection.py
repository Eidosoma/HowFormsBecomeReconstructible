"""D092 short disposable/synthetic checks before full protection outcomes."""
from copy import deepcopy
import inspect
from pathlib import Path

import numpy as np
import pytest

from laws_confirmation import l24_write_protection as p

SHORT=p.source.Config(parents=1,draws=2,settle=4,parent_steps=8,zap=6,child_steps=6,times=(0,1,2,3,6))
WINDOW=p.temporal.Window(active=10,pulse=2,recovery=10)


@pytest.fixture(scope='module')
def example():
    d086,_=p.source.execute_parent(p.source.context(p.source.DISPOSABLE,SHORT),0,p.source.checker())
    d089,_=p.temporal.execute_parent(d086,index=p.source.DISPOSABLE,parent=0,cfg=SHORT,window=WINDOW)
    original,_=p.previous.execute_parent(d089,index=p.source.DISPOSABLE,parent=0,cfg=SHORT,window=WINDOW)
    result,meta=p.execute_parent(original,index=p.source.DISPOSABLE,parent=0,cfg=SHORT,window=WINDOW)
    return original,result,meta


def test_fixed_scope_and_counts():
    c=p.contract()
    assert c['writer_rates']==[.0005,.005] and c['rho']==.002 and c['norm']==.3
    assert c['hold_updates']==[450,500] and c['hold_theta_bit_exact'] and c['hold_projection_disabled']
    assert c['R_always_live'] and not c['R_reset'] and c['reopen_first_update']==500
    assert c['writer_trajectories_evaluated']==8*4*2*3==192 and c['source_writer_trajectories_regenerated']==0
    assert c['descendant_lives_evaluated']==32*2*2*12*8==12288 and c['source_off_anchor_lives_in_count']==6144
    assert c['new_unprotected_descendant_evaluations']==0 and c['source_on_snapshot_metrics_reused']==6144
    assert (c['binary_rows'],c['continuous_rows'],c['writer_rows'],c['child_timing_rows'],c['writer_timing_rows'])==(64,128,64,24,8)
    assert c['primary_contrast']=='fast_minus_slow_pulse_reduction' and c['primary_writer_boundary']==1000
    assert c['scientific_pass_gate'] is None and not c['automatic_followup'] and not c['rate_or_window_search']
    assert c['fast_rate_outside_original_E70_u_range'] and c['clock_gate_engineer_scheduled']
    assert not c['body_feedback'] and c['new_full_parent_lives']==0 and c['new_tissue_blocks']==0
    assert c['packet_bytes']==2048 and c['inherited_fields']==['theta'] and c['theta_frozen_in_descendant']
    assert not c['fitness_or_semantic_selectivity_claim'] and not c['renewal_or_biological_claim']


def test_independent_writer_packets_and_aliases(example):
    original,result,meta=example
    assert p.checker().check_writer(original,result,WINDOW)<=1e-12
    assert p.checker().check_packets(result,WINDOW)<=1e-12
    assert p.checker().check_aliases(original,result)
    assert meta['writer_max_abs']<=1e-12 and meta['packet_max_abs']<=1e-12


def test_hold_is_exact_then_writing_resumes(example):
    original,result,_=example;start=WINDOW.active-WINDOW.pulse
    states=result['writer_states'];begin=states[WINDOW.times.index(start),1];end=states[WINDOW.times.index(WINDOW.active),1]
    np.testing.assert_array_equal(begin,end)
    assert not np.array_equal(end,states[WINDOW.times.index(WINDOW.active+1),1])
    np.testing.assert_array_equal(result['writer_states'][:,0],original['writer_states'][:,0])
    assert not np.array_equal(states[WINDOW.times.index(start),0],states[WINDOW.times.index(WINDOW.active),0])
    np.testing.assert_array_equal(result['records'][0],result['records'][2])
    np.testing.assert_array_equal(result['records'][3],result['records'][5])
    assert not np.array_equal(result['records'][6],result['records'][8])


def test_source_inputs_unchanged(example):
    original,_,_=example;before={k:v.copy() for k,v in original.items()}
    result=p.write_records(original,WINDOW);p.build_packets(result,WINDOW)
    for k,v in before.items(): np.testing.assert_array_equal(original[k],v)


@pytest.mark.parametrize('key',['input_base','input_delta','initial_writer','targets','permutation','schedule','write_enabled',
    'writer_states','writer_trace','proposal_details','R_weights'])
def test_corrupt_writer_detected(example,key):
    original,result,_=deepcopy(example)
    if key=='write_enabled': result[key][WINDOW.active-1]=True
    else: result[key].flat[-1]+=.01 if key!='permutation' else 1
    with pytest.raises(AssertionError): p.checker().check_writer(original,result,WINDOW)


@pytest.mark.parametrize('arm',range(12))
def test_every_packet_checked(example,arm):
    _,result,_=deepcopy(example);result['records'][arm,0,0]+=.01
    with pytest.raises(AssertionError): p.checker().check_packets(result,WINDOW)


@pytest.mark.parametrize('field',range(3))
@pytest.mark.parametrize('arm',[0,2,3,5,6,11])
def test_all_off_source_anchors_checked(example,field,arm):
    original,result,_=deepcopy(example);result['descendants'][0,-1,field,1,arm,0,0,0]+=.1
    with pytest.raises(AssertionError): p.checker().check_aliases(original,result)


@pytest.mark.parametrize('arm',list(range(6))+list(range(12,18)))
def test_all_source_metric_mappings_checked(example,arm):
    original,result,_=deepcopy(example);result['values'][0,-1,0,arm,0,0,2]+=.1
    with pytest.raises(AssertionError): p.checker().check_aliases(original,result)


@pytest.mark.parametrize('reader',[0,1])
def test_independent_child_physics_and_metrics(example,reader):
    _,result,meta=example
    assert p.source.checker().check_descendants(result['descendants'][reader],result['records'],
        p.source.context(p.source.DISPOSABLE,SHORT),0,reader,meta['children'][reader])<=1e-10
    values=np.take(result['values'][reader],p.PROTECTED_INDICES,axis=2)
    assert p.source.checker().check_metrics(result['descendants'][reader],result['targets'],values)


def test_packet_order_does_not_communicate(example):
    _,result,_=example;order=(11,5,1,0,9,7)
    packets=tuple(p.source.encode(result['records'][i]) for i in order)
    assert all(isinstance(x,bytes) and len(x)==2048 for x in packets)
    raw,_=p.source.descendants(packets,index=p.source.DISPOSABLE,parent=0,reader=0,cfg=SHORT)
    np.testing.assert_array_equal(raw,result['descendants'][0][:,:,:,list(order)])


def test_no_source_parent_or_writer_regeneration(example,monkeypatch):
    def forbidden(*args,**kwargs): raise AssertionError('source regeneration forbidden')
    for module,name in ((p.source,'parent_life'),(p.source,'execute_parent'),(p.temporal,'write_records'),
        (p.temporal,'execute_parent'),(p.previous,'write_records'),(p.previous,'execute_parent')):
        monkeypatch.setattr(module,name,forbidden)
    original,expected,_=example
    actual,_=p.execute_parent(original,index=p.source.DISPOSABLE,parent=0,cfg=SHORT,window=WINDOW)
    np.testing.assert_array_equal(actual['descendants'],expected['descendants'])


def test_target_labels_and_body_dynamics_do_not_guide_writing(example,monkeypatch):
    original,expected,_=deepcopy(example);api=p.source.api();original['targets']*=-1
    def forbidden(*args,**kwargs): raise AssertionError('parent body physics excluded')
    monkeypatch.setattr(p.source,'api',lambda:api|{'blueprint_step':forbidden})
    actual=p.write_records(original,WINDOW)
    np.testing.assert_array_equal(actual['writer_states'],expected['writer_states'])
    np.testing.assert_array_equal(actual['write_enabled'],expected['write_enabled'])


@pytest.fixture(scope='module')
def pool_example():
    rng=np.random.default_rng(9201)
    blocks=[dict(values=rng.normal(size=(2,2,5,2,24,2,3,8)),writer_trace=rng.normal(size=(2,21,2,3,2,3,6)),
        reference_writer_trace=rng.normal(size=(2,21,2,3,2,3,6)),proposal_details=rng.normal(size=(2,20,2,3,3)),
        R_weights=rng.normal(size=(2,21,3))) for _ in range(8)]
    return blocks,*p.summarize(blocks,WINDOW)


def test_full_pool_timing_and_fractions_independently_checked(pool_example):
    assert p.checker().check_summary(*pool_example,WINDOW)
    rows=pool_example[2];ratios=p.fractions(rows,WINDOW)
    assert len(ratios)==16 and p.checker().check_fractions(rows,ratios,WINDOW)


@pytest.mark.parametrize('group,position',[(g,i) for g,n in ((2,192),(3,64),(4,24),(5,8)) for i in range(n)])
def test_every_registered_contrast_is_independently_checked(pool_example,group,position):
    data=deepcopy(pool_example);data[group][position]['mean']+=.1
    with pytest.raises(AssertionError): p.checker().check_summary(*data,WINDOW)


@pytest.mark.parametrize('key',['pointwise_block_bootstrap_95','block_means','parent_means','positive','tied','negative',
    'paired_positive','paired_tied','paired_negative','minimum','maximum'])
def test_intervals_units_counts_and_ranges_checked(pool_example,key):
    data=deepcopy(pool_example);row=data[2][0]
    if key=='parent_means': row[key][0][0]+=.1
    elif isinstance(row[key],list): row[key][0]+=.1
    else: row[key]+=.1
    with pytest.raises(AssertionError): p.checker().check_summary(*data,WINDOW)


@pytest.mark.parametrize('key',['means','writer_means','proposal_details_means','R_weights_means'])
def test_all_pooled_arrays_checked(pool_example,key):
    data=deepcopy(pool_example);data[1][key].flat[-1]+=.1
    with pytest.raises(AssertionError): p.checker().check_summary(*data,WINDOW)


@pytest.mark.parametrize('position',range(16))
def test_every_descriptive_fraction_checked(pool_example,position):
    ratios=p.fractions(pool_example[2],WINDOW);ratios[position]['retained_fraction']=.1234567
    with pytest.raises(AssertionError): p.checker().check_fractions(pool_example[2],ratios,WINDOW)


def test_ratio_unavailability_and_no_clipping(pool_example):
    rows=deepcopy(pool_example[2])
    for row in rows:
        if 'unprotected' in row['label']: row['mean']=0.
    ratios=p.fractions(rows,WINDOW)
    assert all(not r['available'] and r['retained_fraction'] is None and r['reduced_fraction'] is None for r in ratios)
    assert p.checker().check_fractions(rows,ratios,WINDOW)
    for row in rows: row['mean']=1. if 'unprotected' in row['label'] else 2.
    assert all(r['retained_fraction']==2. and r['reduced_fraction']==-1. for r in p.fractions(rows,WINDOW))


def test_own_speed_and_protection_baselines_and_interaction_sign():
    v=np.array([1,4,2,10,13,11,100,103,101,1000,1003,1001],float)
    assert p.checker().contrasts(v)[8:14]==(0.,)*6
    v[11]=1000.25  # Fast pulse reduction is now .75, slow reduction remains zero.
    assert p.checker().contrasts(v)[13]==.75
    for i,(_,terms) in enumerate(p.CONTRASTS):
        assert p.previous.previous.difference(v,terms,0)==p.checker().contrasts(v)[i]


def test_external_saved_roundtrip(example,tmp_path):
    _,result,_=example;path=tmp_path/'panel.npz';p.source.base.atomic_npz(path,result,tmp_path)
    with np.load(path,allow_pickle=False) as saved:
        assert set(saved.files)==set(result)
        for key,value in result.items(): np.testing.assert_array_equal(saved[key],value)
    assert '/mnt/bioIce1/' in str(path)


def test_resource_detachment_readonly_and_retention():
    code=inspect.getsource(p.detach)
    for forbidden in ('child.poll(', 'child.wait(', 'time.sleep(', 'while '): assert forbidden not in code
    assert 'start_new_session=True' in code and 'subprocess.DEVNULL' in code
    assert 'max_workers=WORKERS' in inspect.getsource(p.run_experiment) and 'must_detach' in inspect.getsource(p.run_experiment)
    audit=inspect.getsource(p.audit_saved)
    for forbidden in ('check_writer(', 'check_descendants(', 'write_records(', 'atomic_text(', 'strict_json(', 'atomic_npz('): assert forbidden not in audit
    launcher=Path(p.__file__).resolve().parents[2]/p.SCIENCE[3]
    assert 'taskset -c 0-3' in launcher.read_text() and 'PYTHONDONTWRITEBYTECODE=1' in launcher.read_text()
    assert p.source.RESERVE==4*1024**3 and p.source.ALLOWANCE==512*1024**2


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


@pytest.mark.parametrize('key',[None,'contract_sha256','projected_seconds','must_detach','effects_not_reported','freeze_sha256','projected_output_bytes'])
def test_timing_freeze_and_storage_guards(tmp_path,key):
    from laws_confirmation.io import atomic_text
    atomic_text(p.freeze_path(tmp_path),'frozen',tmp_path)
    files={str(tmp_path/'tmp'/f'{p.RUN_ID}_benchmark'/name):'' for name in ('panel.npz','verification.json')}
    for name in files: atomic_text(Path(name),'retained',tmp_path)
    files={name:p.sha256_file(Path(name)) for name in files}
    timing=dict(run_id=p.RUN_ID,passed=True,disposable=p.source.DISPOSABLE,contract_sha256=p.canonical_digest(p.contract()),
        parent_seconds=25.,hash_seconds=1.,projected_seconds=982.,must_detach=True,forecast_does_not_credit_parallel_speedup=True,
        projected_output_bytes=32*8+16*1024**2,effects_not_reported=True,input_sha256={},
        freeze_sha256=p.sha256_file(p.freeze_path(tmp_path)),benchmark_files=files)
    if key is None: assert p.validate_timing(tmp_path,timing,{});return
    timing[key]=False if key in ('must_detach','effects_not_reported') else 'corrupt'
    with pytest.raises(AssertionError): p.validate_timing(tmp_path,timing,{})
