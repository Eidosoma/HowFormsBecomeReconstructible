"""D145 disposable serial physics, boundary isolation, independent frozen statistics."""
import copy
import inspect
import json
import os
from pathlib import Path
import subprocess
import sys
import numpy as np
import pytest
from l20_extension1 import serial_compat_system as system,serial_compat_audit as audit
from l20_extension1 import serial_compat_analysis as analysis,serial_compat_analysis_check as independent
from l20_extension1 import serial_compat_run as run,heldout_system,symmetry_system


def forbidden(*a,**k):raise AssertionError('forbidden dynamics/source/fit access')


@pytest.fixture(scope='module')
def panel(tmp_path_factory):
    guide=system.old.load_guide();raw,meta=system.simulate_life(system.DISPOSABLE,0,guide)
    meta['replay']=audit.check_life(raw,meta,True)
    directory=tmp_path_factory.mktemp('serial_compat_disposable')
    run.io.write_npz(directory/'raw.npz',raw,run.ROOT);run.io.write_json(directory/'meta.json',meta,run.ROOT)
    return dict(raw=raw,meta=meta,directory=directory)


def test_full_disposable_life(panel):
    p=panel['meta']['replay']
    assert p['full_dynamics_replayed'] and p['lineages']==32 and p['paths']==96 and p['enabled_rewrites']==60
    assert p['reader_paths']==192 and p['founder_acquisitions']==2


@pytest.mark.parametrize('role',[0,1])
def test_extreme_classes(role):
    total=[]
    for quarter in system.LEVELS[role]:
        offsets=system.members(role,quarter)
        assert len(offsets)>0 and all(audit.geometry(role,d)==quarter and np.any(d) for d in offsets)
        assert offsets.tolist()==sorted(offsets.tolist());total.extend(map(tuple,offsets))
    assert len(total)==len(set(total))==(31 if role==0 else 63) and (0,0) not in total
    assert len(system.members(role,4))==(15 if role==0 else 31)
    assert len(system.members(role,-4))==(16 if role==0 else 32)


def test_schedule_independence(monkeypatch):
    monkeypatch.setattr(system,'generate_founders',forbidden);monkeypatch.setattr(system,'simulate',forbidden)
    schedule=run.address_schedule()
    assert schedule['outcome_access'] is False and schedule['blocks']==list(range(92000,92016))
    for i in system.BLOCKS:
        for l in range(4):
            for n in (0,1):
                for ci,(r,k) in enumerate(system.CASES):
                    for gi in range(3):
                        np.testing.assert_array_equal(schedule['shifts'][str(i)][l][n][ci][gi],audit.address(i,l,n,r,k,gi+1))
    assert system.CASES==audit.CASES and len(system.CASES)==16


def test_address_ablation_matching():
    for role in (0,1):
        for g in (1,2,3):
            q=system.address(system.DISPOSABLE,0,0,role,'q4',g)
            for kind in ('q4_read_off','q4_write_off'):
                np.testing.assert_array_equal(q,system.address(system.DISPOSABLE,0,0,role,kind,g))
    with pytest.raises(ValueError):system.address(92000,0,0,0,'q4',4)
    with pytest.raises(ValueError):system.address(92000,0,0,0,'q4',True)


def test_matching(panel):
    raw=panel['raw']
    for r in (0,1):
        zero=system.CASES.index((r,'zero'))
        for ci,(role,kind) in enumerate(system.CASES):
            if role!=r:continue
            if not kind.endswith('read_off'):np.testing.assert_array_equal(raw['read_states'][:,ci,0],raw['read_states'][:,zero,0])
            if kind in ('q4','q-4'):np.testing.assert_array_equal(raw['write_states'][:,ci,0,:2],raw['write_states'][:,zero,0,:2])
            for phase in ('read','terminal'):
                np.testing.assert_array_equal(raw[phase+'_states'][:,ci,:,0],raw[phase+'_states'][:,zero,:,0])
    assert not np.array_equal(raw['terminal_states'][0,0,0,0],raw['read_states'][0,0,0,0])
    assert not np.array_equal(raw['read_states'][0,0,0,0],raw['read_states'][1,0,0,0])


def test_serial_continuity(panel):
    raw=panel['raw']
    np.testing.assert_array_equal(raw['incoming'][:,:,1:],raw['outgoing'][:,:,:-1])
    for n in (0,1):
        for ci,(role,kind) in enumerate(system.CASES):
            np.testing.assert_array_equal(raw['incoming'][n,ci,0],raw['founder_packets'][role])
            for gi in range(3):
                assert np.count_nonzero(raw['write_states'][n,ci,gi,0,3])==0
                np.testing.assert_array_equal(raw['write_states'][n,ci,gi,0,:3],raw['read_states'][n,ci,gi,-1])
                if gi:
                    assert not np.array_equal(raw['read_states'][n,ci,gi,0],raw['write_states'][n,ci,gi-1,-1,:3])
                    assert not np.array_equal(raw['read_states'][n,ci,gi,0],raw['terminal_states'][n,ci,gi-1,0])


@pytest.mark.parametrize('generation',[0,1,2])
@pytest.mark.parametrize('key',['incoming','outgoing','read_states','write_states','terminal_states'])
def test_every_boundary_corruption(panel,generation,key):
    raw=panel['raw'].copy();raw[key]=raw[key].copy()
    view=raw[key][0,0,generation]
    if view.dtype==np.uint8:view.flat[0]^=1
    else:view.flat[0]+=1
    with pytest.raises((AssertionError,ValueError)):audit.check_life(raw,panel['meta'],False)


def test_assay_isolation(panel,monkeypatch):
    original=system.assay
    def altered(*args,**kwargs):
        states,meta=original(*args,**kwargs)
        return states+0.007,meta
    monkeypatch.setattr(system,'assay',altered)
    raw=panel['raw'];repeat,_=system.simulate(system.DISPOSABLE,0,0,raw['founder_packets'],raw['guide'])
    for k in ('incoming','outgoing','routed','read_states','write_states','record_values','shift'):
        np.testing.assert_array_equal(repeat[k],raw[k][0])
    assert not np.array_equal(repeat['terminal_states'],raw['terminal_states'][0])


def test_independent_replay(panel,monkeypatch):
    monkeypatch.setattr(system,'simulate_life',forbidden)
    for name in ('read_selected','write_streams','route','record'):monkeypatch.setattr(system.old,name,forbidden)
    assert audit.check_life(panel['raw'],panel['meta'],True)['full_dynamics_replayed']


def test_saved_no_dynamics(panel,monkeypatch):
    monkeypatch.setattr(audit.physics,'step',forbidden)
    assert audit.check_life(panel['raw'],panel['meta'],False)['full_dynamics_replayed'] is False


@pytest.mark.parametrize('key',['incoming','routed','outgoing','terminal_packet','scores','read_states','write_states',
    'terminal_states','read_values','write_values','terminal_values','record_values','shift','founder_packets','f_source_shift','guide'])
def test_corruption(panel,key):
    raw=panel['raw'].copy();raw[key]=raw[key].copy()
    if raw[key].dtype==np.uint8:raw[key].flat[0]^=1
    else:raw[key].flat[0]+=1
    with pytest.raises((AssertionError,ValueError)):audit.check_life(raw,panel['meta'],False)


@pytest.mark.parametrize('key,value',[('tag','old'),('record_bytes',64),('parent_state_access',True),
    ('family_supplied_to_address_rule',False),('writer_receives_target_labels',True),
    ('terminal_is_fresh',False),('guide_refitted',True),('assay_enters_lineage',True),('generations',1)])
def test_metadata_corruption(panel,key,value):
    meta=copy.deepcopy(panel['meta']);meta['trials'][0][key]=value
    with pytest.raises((AssertionError,ValueError)):audit.check_life(panel['raw'],meta,False)


def test_condition_order(panel):
    raw=panel['raw'];repeat,meta=system.simulate(system.DISPOSABLE,0,0,raw['founder_packets'],raw['guide'],tuple(reversed(system.CASES)))
    for k,v in repeat.items():np.testing.assert_array_equal(v,raw[k][0])
    assert meta==panel['meta']['trials'][0]
    with pytest.raises(ValueError):system.simulate(system.DISPOSABLE,0,0,raw['founder_packets'],raw['guide'],system.CASES[:-1])


@pytest.mark.parametrize('index,life,noise',[(91000,0,0),(92016,0,0),(True,0,0),(92000,4,0),(92000,False,0),(92000,0,2),(92000,0,False)])
def test_namespace_guard(index,life,noise):
    with pytest.raises(ValueError):system.rng(index,life,noise,'g1:read')


def test_fresh_founder_namespace(panel):
    assert set(system.BLOCKS).isdisjoint(heldout_system.TISSUES)
    assert set(system.BLOCKS).isdisjoint(symmetry_system.BLOCKS)
    assert system.TAG not in (heldout_system.TAG,symmetry_system.TAG)
    for phase in system.PHASES:
        x=system.rng(92000,0,0,phase).normal(size=16)
        assert not np.array_equal(x,system.rng(92000,0,1,phase).normal(size=16))
        assert not np.array_equal(x,system.old.generator(symmetry_system.TAG,92000,0,'noise0:'+phase).normal(size=16))
    assert panel['meta']['founder']['tag']==system.TAG
    with pytest.raises(ValueError):system.rng(92000,0,0,'unknown')


def test_generation_stream_separation():
    values=[system.rng(92000,0,0,p).normal(size=16).tobytes() for p in system.PHASES]
    assert len(values)==len(set(values))==15
    assert system.PHASES==tuple(f'g{g}:{p}' for g in (1,2,3) for p in ('birth','read','write','terminal_birth','terminal_read'))


def test_zero_shift_bridge(panel):
    raw=panel['raw'];ctx=system.old.context(system.DISPOSABLE);ci=system.CASES.index((1,'zero'))
    for gi in range(3):
        writes,_=system.old.write_streams(raw['read_states'][0,ci,gi,-1],ctx,system.rng(system.DISPOSABLE,0,0,f'g{gi+1}:write'),
            'translated',np.array([0,0],np.int64),system.CONFIG)
        np.testing.assert_array_equal(writes,raw['write_states'][0,ci,gi])


def test_schema_roundtrip(panel):
    meta=run.io.read_json(panel['directory']/'meta.json');raw=run.io.load_npz(panel['directory']/'raw.npz')
    assert 'read_times' not in meta['config'] and meta['config']['steps']==300
    assert isinstance(meta['host']['tissue']['strict_band'],list)
    assert audit.check_life(raw,meta,False)['paths']==96


def test_external_roundtrip(panel):
    raw=run.io.load_npz(panel['directory']/'raw.npz')
    for k in raw:np.testing.assert_array_equal(raw[k],panel['raw'][k])
    with pytest.raises(FileExistsError):run.io.write_npz(panel['directory']/'raw.npz',raw,run.ROOT)


def test_no_source_mutation(panel):
    raw=panel['raw'];founders=raw['founder_packets'].copy();guide=raw['guide'].copy()
    for ci,(role,kind) in enumerate(system.CASES):
        for n in (0,1):
            np.testing.assert_array_equal(raw['incoming'][n,ci,0],founders[role])
            if kind=='copy':
                np.testing.assert_array_equal(raw['outgoing'][n,ci],np.repeat(founders[role,None],3,axis=0))
                np.testing.assert_array_equal(raw['incoming'][n,ci],raw['outgoing'][n,ci])
        if kind.endswith('write_off'):assert not np.count_nonzero(raw['outgoing'][:,ci])
    np.testing.assert_array_equal(raw['guide'],guide)


def test_sixteen_block_normalization():
    x=np.broadcast_to(np.arange(16,dtype=float)[:,None,None],(16,4,2))
    draws=np.tile(np.arange(16),(10000,1));actual=analysis.stats(x,draws)
    assert actual['mean']==7.5 and actual['pointwise_block_bootstrap_95']==[7.5,7.5]
    assert actual['block_means']==list(np.arange(16,dtype=float))
    audit.physics.nested(actual,independent.stats(x,draws))
    with pytest.raises(ValueError):analysis.stats(x[:8],draws)


def test_block_bootstrap():
    x=np.arange(128,dtype=float).reshape(16,4,2)/128;draws=np.zeros((10000,16),int)
    actual=analysis.stats(x,draws);expected=x[0].sum()/8
    assert actual['pointwise_block_bootstrap_95']==[expected,expected]
    audit.physics.nested(actual,independent.stats(x,draws))


def synthetic(effect=0.):
    blocks=[];records=[]
    for bi in range(16):
        block={p+'_values':np.zeros((4,2,16,3,t,2)) for p,t in (('read',5),('write',4),('terminal',4))}
        block['record_values']=np.zeros((4,2,16,3,2));block['shift']=np.zeros((4,2,16,3,2),np.int64)
        for ci,(role,kind) in enumerate(system.CASES):
            value=.2 if not kind.endswith(('read_off','write_off')) else 0.
            if kind=='q4' and role==1:value+=effect
            block['terminal_values'][:,:,ci,:,-1,0]=value
            block['record_values'][:,:,ci,:,1]=.4+(.4 if kind=='q4' else 0.)
        blocks.append(block)
        records.append(dict(lives=[dict(trials=[dict(paths=[dict(generations=[
            dict(terminal_selector=dict(inferred_family=r)) for gi in range(3)]) for r,k in system.CASES])
            for n in (0,1)]) for l in range(4)]))
    return blocks,records


def test_complete_summary(monkeypatch):
    blocks,records=synthetic(.125);s=analysis.summarize(blocks,records)
    monkeypatch.setattr(analysis,'summarize',forbidden);monkeypatch.setattr(analysis,'stats',forbidden)
    assert independent.check(s,blocks,records)['passes']
    assert s['label']=='B_COMPATIBLE_SERIAL_BENEFIT' and s['primary']['mean']==.125
    assert len(s['groups'])==48 and len(s['contrasts'])==42 and len(s['controls'])==30
    assert len(s['copy_contrasts'])==6 and len(s['serial_changes'])==16 and len(s['advantage_changes'])==2
    s['primary']['mean']+=.01
    with pytest.raises(AssertionError):independent.check(s,blocks,records)


def test_primary_not_shape():
    b,m=synthetic(-.0625);s=analysis.summarize(b,m)
    assert s['label']=='B_COMPATIBLE_SERIAL_HARM' and s['primary']['mean']==-.0625
    assert next(v for v in s['contrasts'] if (v['role'],v['condition'],v['generation'])==(1,'q4',3))['metrics']['outgoing_shape']['mean']>0
    assert independent.check(s,b,m)['passes']


def test_late_primary():
    b,m=synthetic(.125);q=system.CASES.index((1,'q4'))
    for block in b:block['terminal_values'][:,:,q,2,-1,0]=.2-.0625
    s=analysis.summarize(b,m)
    assert s['label']=='B_COMPATIBLE_SERIAL_HARM' and s['primary']['mean']==-.0625
    assert next(v for v in s['contrasts'] if (v['role'],v['condition'],v['generation'])==(1,'q4',1))['metrics']['terminal_preference']['mean']==.125
    assert independent.check(s,b,m)['passes']


def test_control_gate_not_primary():
    b,m=synthetic(.125);off=system.CASES.index((0,'q4_read_off'))
    for block in b:block['terminal_values'][:,:,off,0,-1,0]=.9
    s=analysis.summarize(b,m)
    assert s['label']=='APPARATUS_NOT_QUALIFIED' and s['primary_interval_classification']=='B_COMPATIBLE_SERIAL_BENEFIT'
    assert not s['apparatus_qualified'] and s['primary']['mean']==.125
    assert independent.check(s,b,m)['passes']


def test_constant_unresolved():
    b,m=synthetic();s=analysis.summarize(b,m)
    assert s['label']=='B_COMPATIBLE_SERIAL_UNRESOLVED' and s['primary']['pointwise_block_bootstrap_95']==[0.,0.]
    assert s['equivalence_test'] is False and independent.check(s,b,m)['passes']


def test_source_closure():
    files=run.source_closure();assert len(files)>=1450
    assert all(system.dev.WS/p in files for p in run.SCIENCE)
    assert system.dev.WS/'compatible-feedback/RESULTS.md' in files
    assert system.dev.WS/'serial-compatible-feedback/README.md' not in files


def test_resource_guards(monkeypatch):
    assert len(run.preflight())<=6
    monkeypatch.setenv('OMP_NUM_THREADS','2')
    with pytest.raises((RuntimeError,AssertionError)):run.preflight()


def test_detached_guard(monkeypatch):
    monkeypatch.delenv(run.DETACHED_ENV,raising=False)
    with pytest.raises(RuntimeError):run.detached_guard(True)
    run.detached_guard(False)
    assert 'select.select([ready_read], [], [], 55)' in inspect.getsource(run.detach)
    assert 'child.poll' not in inspect.getsource(run.detach)


def test_startup_handshake(monkeypatch):
    rd,wr=os.pipe();monkeypatch.setenv('D145_READY_FD',str(wr));run.signal_ready('execute')
    try:assert json.loads(os.read(rd,4096))==dict(stage='execute',pid=os.getpid(),status='STARTED')
    finally:os.close(rd)


def test_no_automatic_successor():
    assert run.contract()['automatic_successor'] is False and run.contract()['automatic_polling'] is False
    assert 'execute(' not in inspect.getsource(run.benchmark) and 'prepare(' not in inspect.getsource(run.benchmark)
    assert 'detach(' not in inspect.getsource(run.execute)


def test_main_barrier(monkeypatch,tmp_path):
    monkeypatch.setattr(system,'simulate_life',forbidden)
    with pytest.raises(ValueError):run.worker(tmp_path,92000)
    monkeypatch.setattr(run,'barrier',lambda *a:(_ for _ in ()).throw(RuntimeError('no seal')))
    with pytest.raises(RuntimeError):run.worker(tmp_path,92000,tmp_path,'not-a-manifest')
    assert run.contract()['all_addresses_before_any_founders'] is True


def test_cold_benchmark_audit_initializes():
    code="""from l20_extension1 import serial_compat_run as r
def stop_after_preflight():
    import voltage_web
    assert r.system.old.context(514245)['api'] is not None
    raise LookupError('cold initialization checked')
r.frozen=stop_after_preflight
try:r.benchmark_audit()
except LookupError as e:
    assert str(e)=='cold initialization checked'
    print('cold initialization checked')
else:raise AssertionError('sentinel not reached')
"""
    process=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True,check=False,timeout=30)
    assert process.returncode==0,(process.stdout,process.stderr)
    assert 'cold initialization checked' in process.stdout


def test_failure_receipt(tmp_path,monkeypatch):
    monkeypatch.setattr(run,'preflight',lambda:None);monkeypatch.setattr(run,'frozen',lambda:{'test_proof':{'benchmark_forecast':0}})
    directory=tmp_path/'failed_benchmark';monkeypatch.setattr(run,'benchmark_dir',lambda:directory)
    monkeypatch.setattr(run,'worker',lambda *a:(_ for _ in ()).throw(RuntimeError('synthetic failure')))
    with pytest.raises(RuntimeError):run.benchmark()
    assert (directory/'FAILED.json').exists() and not (directory/'score_fixture.json').exists()
