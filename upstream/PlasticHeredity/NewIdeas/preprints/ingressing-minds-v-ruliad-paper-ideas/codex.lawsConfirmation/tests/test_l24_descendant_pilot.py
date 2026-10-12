"""D086: short disposable and synthetic checks only; no new panel outcomes."""
from copy import deepcopy
from dataclasses import asdict, replace
import inspect
import json
from pathlib import Path

import numpy as np
import pytest

from laws_confirmation import l24_descendant_pilot as p

SHORT=p.Config(parents=1,draws=2,settle=4,parent_steps=8,zap=6,child_steps=6,times=(0,1,2,3,6))


@pytest.fixture(scope='module')
def example():
    ctx=p.context(p.DISPOSABLE,SHORT);check=p.checker()
    clean,cm=p.parent_life(ctx,0,False);damaged,dm=p.parent_life(ctx,0,True)
    records,targets,permutation=p.make_records(ctx,0,clean,damaged)
    payload,meta=p.execute_parent(ctx,0,check)
    return dict(ctx=ctx,check=check,clean=clean,damaged=damaged,cm=cm,dm=dm,
                records=records,targets=targets,permutation=permutation,payload=payload,meta=meta)


def test_registered_contract():
    c=p.contract()
    assert c['decision']=='D086' and c['boundaries']==1 and c['packet_bytes']==2048
    assert c['writer_speed_sweep'] is False and c['protection_factorial'] is False
    assert c['scientific_pass_gate'] is None and c['automatic_followup'] is False
    assert c['original_writer_rate']==.0005 and c['norm']==.3
    assert p.DISPOSABLE not in p.TISSUES and len(p.TISSUES)==8
    assert c['parent_lives']==len(p.TISSUES)*p.CONFIG.parents*2==64
    assert c['descendant_lives']==len(p.TISSUES)*p.CONFIG.parents*2*2*8*p.CONFIG.draws==8192
    assert c['inherited_fields']==['theta'] and c['R_V_ema_not_transmitted']
    ctx=p.context(p.DISPOSABLE)
    assert ctx['bp'].c_m==.2 and ctx['bp'].rho==.002
    assert ctx['api']['WeismannConfig']().rho*.5/2==p.CONFIG.writer_rate


@pytest.mark.parametrize('changes',[dict(parents=0),dict(draws=0),dict(settle=0),dict(zap=0),
    dict(zap=7),dict(times=(0,2,1,6)),dict(times=(1,6)),dict(times=(0,3,5)),dict(norm=float('nan')),
    dict(writer_rate=0),dict(writer_rate=1),dict(writer_rate=float('nan'))])
def test_config_rejects_bad_clocks(changes):
    with pytest.raises(ValueError): replace(SHORT,**changes)


@pytest.mark.parametrize('damaged',[False,True])
def test_exact_source_bridge_and_independent_parent(example,damaged):
    key,metadata=('damaged','dm') if damaged else ('clean','cm')
    result=example['check'].check_parent(example[key],example['ctx'],0,damaged,example[metadata])
    assert result['passed'] and result['source_bridge']['exact_states']
    assert result['replay_max_abs']<=1e-10


def test_damage_clock_and_ema_reset(example):
    clean,damaged=example['clean'],example['damaged']
    assert clean['states'].shape==(7,4,16,16)
    np.testing.assert_array_equal(clean['states'][:4],damaged['states'][:4])
    np.testing.assert_array_equal(damaged['states'][3,2:],damaged['states'][4,2:])
    np.testing.assert_array_equal(damaged['states'][4,0],damaged['states'][4,1])
    assert example['cm']['rng_final']==example['dm']['rng_final']
    assert clean['fresh'].sum()==128 and clean['zone'].sum()==64


@pytest.mark.parametrize('field',range(4))
def test_parent_checker_rejects_corrupt_fields(example,field):
    raw=deepcopy(example['damaged']);raw['states'][-1,field,0,0]+=.01
    with pytest.raises(AssertionError): example['check'].check_parent(raw,example['ctx'],0,True,example['dm'])


@pytest.mark.parametrize('key',['fresh','founder','zone'])
def test_parent_checker_rejects_corrupt_masks(example,key):
    raw=deepcopy(example['clean']);raw[key][0,0]=not raw[key][0,0]
    with pytest.raises(AssertionError): example['check'].check_parent(raw,example['ctx'],0,False,example['cm'])


@pytest.mark.parametrize('kind',['rng','fitness','leak'])
def test_parent_checker_rejects_bad_metadata(example,kind):
    meta=deepcopy(example['dm'])
    if kind=='rng': meta['rng_final']='bad'
    else: meta['source_metrics'][kind]=-.5
    with pytest.raises(AssertionError): example['check'].check_parent(example['damaged'],example['ctx'],0,True,meta)


def test_source_spies_are_restored_on_failure(example,monkeypatch):
    source=example['ctx']['api']['original'];before=(source.blueprint_step,source.fission_with_mask)
    def fail(*args,**kwargs): raise RuntimeError('injected source failure')
    monkeypatch.setattr(source,'life_fitness',fail)
    with pytest.raises(RuntimeError):
        example['check'].source_bridge(example['clean'],example['ctx'],0,False,example['cm'])
    assert (source.blueprint_step,source.fission_with_mask)==before


def test_record_controls(example):
    e=example
    assert e['check'].check_records(e['records'],e['targets'],e['permutation'],e['clean'],e['damaged'],e['ctx'],0)
    np.testing.assert_array_equal(np.sort(e['records'][5].ravel()),np.sort(e['records'][6].ravel()))
    np.testing.assert_array_equal(e['records'][5],-e['records'][7])
    assert not e['records'][2].any()


@pytest.mark.parametrize('record',range(8))
def test_record_checker_rejects_corruption(example,record):
    e=example;records=e['records'].copy();records[record,1,1]+=.01
    with pytest.raises(AssertionError):
        e['check'].check_records(records,e['targets'],e['permutation'],e['clean'],e['damaged'],e['ctx'],0)


def test_exact_packet_and_readonly_decode(example):
    for record in example['records']:
        packet=p.encode(record)
        assert type(packet) is bytes and len(packet)==2048
        restored=p.decode(packet);assert not restored.flags.writeable
        np.testing.assert_array_equal(restored,record)
        with pytest.raises(ValueError): restored[0,0]=99


@pytest.mark.parametrize('bad',[None,b'',bytes(2047),bytes(2049),bytearray(2048),{'theta':bytes(2048)},
    np.full((16,16),np.nan).tobytes(),np.full((16,16),np.inf).tobytes()])
def test_decode_rejects_wrong_packet(bad):
    with pytest.raises(ValueError): p.decode(bad)


@pytest.mark.parametrize('bad',[None,np.zeros((8,32)),np.zeros((16,16),np.float32),np.full((16,16),np.nan)])
def test_encode_rejects_bad_field(bad):
    with pytest.raises(ValueError): p.encode(bad)


@pytest.mark.parametrize('reader',[0,1])
def test_descendant_api_and_replay(example,reader):
    raw=example['payload']['descendants'][reader];meta=example['meta']['children'][reader]
    assert example['check'].check_descendants(raw,example['records'],example['ctx'],0,reader,meta)<=1e-10
    names=set(inspect.signature(p.descendants).parameters)
    assert names=={'packets','index','parent','reader','cfg'}


@pytest.mark.parametrize('reader',[0,1])
def test_packets_cannot_communicate_across_batch(example,reader):
    order=(7,3,2,0,6,1,5,4);packets=tuple(p.encode(example['records'][i]) for i in order)
    reordered,_=p.descendants(packets,index=p.DISPOSABLE,parent=0,reader=reader,cfg=SHORT)
    expected=example['payload']['descendants'][reader]
    np.testing.assert_array_equal(reordered,expected[:,:,:,list(order)])
    single,_=p.descendants((packets[0],),index=p.DISPOSABLE,parent=0,reader=reader,cfg=SHORT)
    np.testing.assert_array_equal(single[:,:,:,0],expected[:,:,:,7])
    # An unrelated record may change arbitrarily without changing packet zero.
    other,_=p.descendants((packets[0],p.encode(np.full((16,16),.19))),index=p.DISPOSABLE,parent=0,reader=reader,cfg=SHORT)
    np.testing.assert_array_equal(single[:,:,:,0],other[:,:,:,0])


def test_no_parent_arrays_are_inputs_and_no_birth_state_bias(example):
    parent=deepcopy(example['clean']);packets=tuple(p.encode(x) for x in example['records'])
    parent['states'][:]=999  # unused after writing the packet
    raw,_=p.descendants(packets,index=p.DISPOSABLE,parent=0,reader=0,cfg=SHORT)
    np.testing.assert_array_equal(raw,example['payload']['descendants'][0])
    assert example['check'].check_aliases(example['payload'])
    with pytest.raises(TypeError): p.descendants(packets,index=p.DISPOSABLE,parent=0,reader=0,cfg=SHORT,parent_state=parent)


@pytest.mark.parametrize('field',range(3))
def test_child_checker_rejects_corrupt_field(example,field):
    raw=example['payload']['descendants'][0].copy();raw[-1,field,0,0,0,0,0]+=.01
    with pytest.raises(AssertionError):
        example['check'].check_descendants(raw,example['records'],example['ctx'],0,0,example['meta']['children'][0])


@pytest.mark.parametrize('metric',range(8))
def test_metric_corruption_is_detected(example,metric):
    raw=example['payload']['descendants'][0];values=example['payload']['values'][0].copy()
    assert example['check'].check_metrics(raw,example['targets'],values)
    values[-1,0,0,0,0,metric]+=.1
    with pytest.raises(AssertionError): example['check'].check_metrics(raw,example['targets'],values)


def test_npz_roundtrip(example,tmp_path):
    target=tmp_path/'d086_short.npz'
    p.base.atomic_npz(target,example['payload'],tmp_path)
    with np.load(target,allow_pickle=False) as saved:
        for key,value in example['payload'].items(): np.testing.assert_array_equal(saved[key],value)
    assert '/mnt/bioIce1/' in str(target)


@pytest.fixture(scope='module')
def synthetic_pool():
    random=np.random.default_rng(894)
    blocks=[random.uniform(0,1,(2,2,5,2,8,3,3,8)) for _ in range(8)]
    return blocks,*p.summarize(blocks)


def test_independent_pool(synthetic_pool):
    assert p.checker().check_summary(*synthetic_pool)


@pytest.mark.parametrize('row',range(8))
@pytest.mark.parametrize('key',['mean','positive','pointwise_block_bootstrap_95'])
def test_pool_rejects_corrupt_focal(synthetic_pool,row,key):
    blocks,summary,focal=deepcopy(synthetic_pool)
    if key=='pointwise_block_bootstrap_95': focal[row][key][0]+=.2
    else: focal[row][key]+=1
    with pytest.raises(AssertionError): p.checker().check_summary(blocks,summary,focal)


def test_pool_rejects_bad_axes(synthetic_pool):
    blocks,summary,focal=deepcopy(synthetic_pool);summary['means'][0,0,0,0,0,0]+=.1
    with pytest.raises(AssertionError): p.checker().check_summary(blocks,summary,focal)


def test_production_orchestration_has_caps_and_no_child_poll():
    source=inspect.getsource(p.detach)
    assert 'start_new_session=True' in source and 'subprocess.DEVNULL' in source
    for forbidden in ('child.poll(', 'child.wait(', 'time.sleep(', 'while '): assert forbidden not in source
    run=inspect.getsource(p.run_experiment)
    assert 'max_workers=WORKERS' in run and 'must_detach' in run and 'LAUNCH.lock' in run
    launcher=Path(p.__file__).resolve().parents[2]/p.SCIENCE[3]
    assert 'taskset -c 0-3' in launcher.read_text()


def test_disk_and_cpu_preflight(monkeypatch,tmp_path):
    for key in ('TMPDIR','XDG_CACHE_HOME'): monkeypatch.setenv(key,str(tmp_path/'cache'))
    (tmp_path/'cache').mkdir()
    for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','PYTHONDONTWRITEBYTECODE'):
        monkeypatch.setenv(key,'1')
    monkeypatch.setattr(p.os,'sched_getaffinity',lambda _: {0,1,2,3})
    from collections import namedtuple
    Usage=namedtuple('Usage','total used free')
    monkeypatch.setattr(p.shutil,'disk_usage',lambda _:Usage(20*1024**3,0,10*1024**3))
    assert p.preflight(tmp_path)==[0,1,2,3]
    monkeypatch.setattr(p.os,'sched_getaffinity',lambda _: {0,1,2,3,4})
    with pytest.raises(RuntimeError): p.preflight(tmp_path)
    monkeypatch.setattr(p.os,'sched_getaffinity',lambda _: {0})
    monkeypatch.setattr(p.shutil,'disk_usage',lambda _:Usage(20*1024**3,0,p.RESERVE))
    with pytest.raises(RuntimeError): p.preflight(tmp_path)
    assert p.preflight(tmp_path,starting=False)==[0]


def test_freeze_guard_detects_changed_inputs(monkeypatch,tmp_path):
    from laws_confirmation.io import atomic_text
    path=tmp_path/'source.txt';atomic_text(path,'v1',tmp_path)
    monkeypatch.setattr(p,'input_paths',lambda root:[path])
    monkeypatch.setattr(p,'source_verified',lambda root,hashes:True)
    record=dict(contract=p.contract(),full_duration_new_outcomes_seen=False,input_sha256={str(path):p.sha256_file(path)})
    p.strict_json(p.freeze_path(tmp_path),record,tmp_path)
    assert p.frozen_inputs(tmp_path)==record['input_sha256']
    atomic_text(path,'v2',tmp_path)
    with pytest.raises(AssertionError): p.frozen_inputs(tmp_path)


def test_source_bridge_is_not_original_eight_cycle_claim():
    assert p.CONFIG.parent_steps==500 and p.CONFIG.settle==120
    assert p.contract()['source_life_fitness_cycles']==1
    assert p.context(p.DISPOSABLE)['api']['WeismannConfig']().cycles==8


@pytest.mark.parametrize('bad_key',[None,'run_id','passed','disposable','config','projected_seconds',
    'must_detach','effects_not_reported','forecast_does_not_credit_parallel_speedup','freeze_sha256','benchmark_files'])
def test_timing_and_provenance_guard(tmp_path,bad_key):
    from laws_confirmation.io import atomic_text
    freeze=p.freeze_path(tmp_path);atomic_text(freeze,'frozen',tmp_path)
    directory=tmp_path/'tmp'/f'{p.RUN_ID}_benchmark'
    files={str(directory/name):'placeholder' for name in ('panel.npz','verification.json')}
    for name in files: atomic_text(Path(name),'retained',tmp_path)
    files={name:p.sha256_file(Path(name)) for name in files}
    forecast=32*25.+2*1.+180
    timing=dict(run_id=p.RUN_ID,passed=True,disposable=p.DISPOSABLE,config=asdict(p.CONFIG),
        parent_seconds=25.,hash_seconds=1.,projected_seconds=forecast,must_detach=True,effects_not_reported=True,
        forecast_does_not_credit_parallel_speedup=True,input_sha256={},freeze_sha256=p.sha256_file(freeze),benchmark_files=files)
    if bad_key is None:
        assert p.validate_timing(tmp_path,timing,{})
        return
    if bad_key in ('passed','must_detach','effects_not_reported','forecast_does_not_credit_parallel_speedup'):
        timing[bad_key]=False
    elif bad_key=='config': timing['config']['draws']=9
    elif bad_key=='benchmark_files': timing['benchmark_files']={}
    else: timing[bad_key]='corrupted'
    with pytest.raises(AssertionError): p.validate_timing(tmp_path,timing,{})
