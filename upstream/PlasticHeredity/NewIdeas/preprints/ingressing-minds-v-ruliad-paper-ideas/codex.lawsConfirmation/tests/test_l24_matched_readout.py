"""D088 synthetic/short-disposable tests; no full-duration new control outcomes."""
from copy import deepcopy
from dataclasses import asdict
import inspect
from pathlib import Path

import numpy as np
import pytest

from laws_confirmation import l24_matched_readout as p

SHORT=p.source.Config(parents=1,draws=2,settle=4,parent_steps=8,zap=6,child_steps=6,times=(0,1,2,3,6))


@pytest.fixture(scope='module')
def example():
    original,_=p.source.execute_parent(p.source.context(p.source.DISPOSABLE,SHORT),0,p.source.checker())
    result,meta=p.execute_parent(original,index=p.source.DISPOSABLE,parent=0,cfg=SHORT)
    return original,result,meta


def test_registered_scope_and_counts():
    c=p.contract()
    assert c['decision']=='D088' and len(p.RECORDS)==7 and c['summary_rows']==42
    assert c['daughter_lives_evaluated']==8*4*2*2*7*8==7168
    assert c['source_anchor_lives_in_evaluated_count']==2048 and c['new_control_condition_lives_in_evaluated_count']==5120
    assert c['parent_lives_generated']==0 and c['new_tissue_blocks']==0 and not c['writer_rates_changed']
    assert c['scientific_pass_gate'] is None and not c['automatic_followup']
    assert c['packet_bytes']==2048 and c['inherited_fields']==['theta']
    assert not c['regional_energy_matched'] and not c['optimal_reader_direction_claim']


def test_all_geometry_independently_checked(example):
    original,result,meta=example
    assert p.checker().check_geometry(original,result)<=1e-12 and meta['source_anchors_exact']
    r,d=result['geometry_parameters'][:2]
    np.testing.assert_allclose(result['geometry'][:,0],r,rtol=0,atol=1e-12)
    np.testing.assert_allclose(result['geometry'][1:,1],d,rtol=0,atol=1e-12)
    assert not result['geometry_energy_available'][0] and result['geometry_energy_available'][1:].all()
    assert all(len(p.source.encode(x))==2048 for x in result['records'])


def test_inputs_are_unchanged(example):
    original,_,_=example;before={k:v.copy() for k,v in original.items()}
    p.construct(original)
    for k in before: np.testing.assert_array_equal(original[k],before[k])


@pytest.mark.parametrize('record',range(7))
def test_corrupt_record_detected(example,record):
    original,result,_=deepcopy(example);result['records'][record,0,0]+=.0001
    with pytest.raises(AssertionError): p.checker().check_geometry(original,result)


@pytest.mark.parametrize('key',['directions','units','geometry','geometry_parameters','reconstructed_actual','targets','permutation'])
def test_corrupt_geometry_metadata_detected(example,key):
    original,result,_=deepcopy(example);result[key].flat[0]+=1
    with pytest.raises(AssertionError): p.checker().check_geometry(original,result)


@pytest.mark.parametrize('mode',['zero_chord','antipodal','bad_norm','constant_goal','radial_goal'])
def test_invalid_geometry_fails_without_substitution(example,mode):
    original,_,_=deepcopy(example);b=original['records'][0]
    if mode=='zero_chord': original['records'][1]=b
    elif mode=='antipodal': original['records'][1]=-b
    elif mode=='bad_norm': original['records'][0]=2*b
    elif mode=='constant_goal': original['records'][5]=original['records'][4]+.2
    else: original['records'][5]=original['records'][4]+b
    with pytest.raises(ValueError): p.construct(original)


def test_plain_record_negation_is_not_the_control(example):
    original,result,_=deepcopy(example)
    assert p.rms(result['records'][3]-result['records'][0])<1e-3
    assert p.rms(-result['records'][2]-result['records'][0])>.59
    result['records'][3]=-result['records'][2]
    with pytest.raises(AssertionError): p.checker().check_geometry(original,result)


def test_tangent_orientation_and_exact_actual_reconstruction(example):
    original,result,_=example;b=original['records'][0]
    for unit in result['units']:
        np.testing.assert_allclose(np.mean(unit*b),0,rtol=0,atol=1e-12)
        np.testing.assert_allclose(p.rms(unit),1,rtol=0,atol=1e-12)
    np.testing.assert_allclose(result['reconstructed_actual'],original['records'][1],rtol=0,atol=1e-12)


def test_exact_anchors_and_off_controls(example):
    original,result,_=example
    assert p.checker().check_anchors_and_aliases(original,result)


@pytest.mark.parametrize('field',range(3))
def test_anchor_corruption_detected(example,field):
    original,result,_=deepcopy(example);result['descendants'][0,-1,field,0,1,0,0,0]+=.001
    with pytest.raises(AssertionError): p.checker().check_anchors_and_aliases(original,result)


@pytest.mark.parametrize('reader',[0,1])
def test_independent_dynamics_replay(example,reader):
    _,result,meta=example
    error=p.source.checker().check_descendants(result['descendants'][reader],result['records'],
        p.source.context(p.source.DISPOSABLE,SHORT),0,reader,meta['children'][reader])
    assert error<=1e-10


@pytest.mark.parametrize('reader',[0,1])
def test_record_reordering_and_singletons_do_not_communicate(example,reader):
    _,result,_=example;order=(6,3,0,5,1,4,2)
    packets=tuple(p.source.encode(result['records'][i]) for i in order)
    raw,_=p.source.descendants(packets,index=p.source.DISPOSABLE,parent=0,reader=reader,cfg=SHORT)
    np.testing.assert_array_equal(raw,result['descendants'][reader][:,:,:,list(order)])
    single,_=p.source.descendants((packets[0],),index=p.source.DISPOSABLE,parent=0,reader=reader,cfg=SHORT)
    np.testing.assert_array_equal(single[:,:,:,0],raw[:,:,:,0])


def test_production_does_not_regenerate_parents(example,monkeypatch):
    def forbidden(*args,**kwargs): raise AssertionError('parent regeneration forbidden')
    monkeypatch.setattr(p.source,'parent_life',forbidden);monkeypatch.setattr(p.source,'execute_parent',forbidden)
    original,expected,_=example
    actual,_=p.execute_parent(original,index=p.source.DISPOSABLE,parent=0,cfg=SHORT)
    np.testing.assert_array_equal(actual['descendants'],expected['descendants'])


@pytest.fixture(scope='module')
def pool_example():
    random=np.random.default_rng(8801)
    blocks=[random.uniform(size=(2,2,5,2,7,2,3,8)) for _ in range(8)]
    old_blocks=[np.pad(b,((0,0),(0,0),(0,0),(0,0),(0,1),(0,0),(0,0),(0,0))) for b in blocks]
    _,old_focal=p.source.summarize(old_blocks)
    return blocks,*p.summarize(blocks),old_focal


def test_all_three_observers_and_source_pool_bridge(pool_example):
    assert p.checker().check_summary(*pool_example)


@pytest.mark.parametrize('row',range(42))
def test_every_focal_and_continuous_row_checked(pool_example,row):
    blocks,summary,rows,old=deepcopy(pool_example);rows[row]['mean']+=.1
    with pytest.raises(AssertionError): p.checker().check_summary(blocks,summary,rows,old)


@pytest.mark.parametrize('key',['pointwise_block_bootstrap_95','block_means','parent_means'])
def test_interval_and_unit_values_checked(pool_example,key):
    blocks,summary,rows,old=deepcopy(pool_example)
    if key=='parent_means': rows[0][key][0][0]+=.1
    else: rows[0][key][0]+=.1
    with pytest.raises(AssertionError): p.checker().check_summary(blocks,summary,rows,old)


@pytest.mark.parametrize('key',['positive','tied','negative','paired_positive','paired_tied','paired_negative'])
def test_sign_counts_checked(pool_example,key):
    blocks,summary,rows,old=deepcopy(pool_example);rows[0][key]+=1
    with pytest.raises(AssertionError): p.checker().check_summary(blocks,summary,rows,old)


def test_source_anchor_summary_cannot_drift(pool_example):
    blocks,summary,rows,old=deepcopy(pool_example);old[3]['mean']+=.001
    with pytest.raises(AssertionError): p.checker().check_summary(blocks,summary,rows,old)


def test_external_npz_roundtrip(example,tmp_path):
    _,result,_=example;path=tmp_path/'weak_records.npz';p.source.base.atomic_npz(path,result,tmp_path)
    with np.load(path,allow_pickle=False) as saved:
        for key,value in result.items(): np.testing.assert_array_equal(saved[key],value)
    assert '/mnt/bioIce1/' in str(path)


def test_resource_caps_and_detached_no_polling():
    source=inspect.getsource(p.detach)
    for forbidden in ('child.poll(', 'child.wait(', 'time.sleep(', 'while '): assert forbidden not in source
    assert 'start_new_session=True' in source and 'subprocess.DEVNULL' in source
    assert 'max_workers=WORKERS' in inspect.getsource(p.run_experiment)
    assert 'must_detach' in inspect.getsource(p.run_experiment)
    launcher=Path(p.__file__).resolve().parents[2]/p.SCIENCE[3]
    assert 'taskset -c 0-3' in launcher.read_text() and 'PYTHONDONTWRITEBYTECODE=1' in launcher.read_text()


def test_immutable_freeze_and_no_retry(monkeypatch,tmp_path):
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


@pytest.mark.parametrize('key',[None,'records','projected_seconds','must_detach','effects_not_reported','freeze_sha256'])
def test_timing_guard(tmp_path,key):
    from laws_confirmation.io import atomic_text
    atomic_text(p.freeze_path(tmp_path),'frozen',tmp_path)
    files={str(tmp_path/'tmp'/f'{p.RUN_ID}_benchmark'/name):'' for name in ('panel.npz','verification.json')}
    for name in files: atomic_text(Path(name),'retained',tmp_path)
    files={name:p.sha256_file(Path(name)) for name in files}
    timing=dict(run_id=p.RUN_ID,passed=True,disposable=p.source.DISPOSABLE,config=asdict(p.source.CONFIG),records=list(p.RECORDS),
        parent_seconds=25.,hash_seconds=1.,projected_seconds=982.,must_detach=True,effects_not_reported=True,
        forecast_does_not_credit_parallel_speedup=True,input_sha256={},freeze_sha256=p.sha256_file(p.freeze_path(tmp_path)),benchmark_files=files)
    if key is None: assert p.validate_timing(tmp_path,timing,{});return
    if key=='records': timing[key]=[]
    elif key in ('must_detach','effects_not_reported'): timing[key]=False
    else: timing[key]='corrupted'
    with pytest.raises(AssertionError): p.validate_timing(tmp_path,timing,{})
