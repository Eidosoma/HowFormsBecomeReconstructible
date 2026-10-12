"""D144 qualification: disposable physics, complete saved checks, synthetic inference."""
import copy
import inspect
import json
import os
from pathlib import Path
import numpy as np
import pytest
from l20_extension1 import symmetry_system as system,symmetry_audit as audit
from l20_extension1 import symmetry_analysis as analysis,symmetry_analysis_check as independent
from l20_extension1 import symmetry_run as run,heldout_system


def forbidden(*a,**k):raise AssertionError('forbidden dynamics/source/fit access')


@pytest.fixture(scope='module')
def panel(tmp_path_factory):
    guide=system.old.load_guide(); raw,meta=system.simulate_life(system.DISPOSABLE,0,guide)
    meta['replay']=audit.check_life(raw,meta,True)
    directory=tmp_path_factory.mktemp('symmetry_disposable')
    run.io.write_npz(directory/'raw.npz',raw,run.ROOT);run.io.write_json(directory/'meta.json',meta,run.ROOT)
    return dict(raw=raw,meta=meta,directory=directory)


def test_full_disposable_life(panel):
    proof=panel['meta']['replay']
    assert proof['full_dynamics_replayed'] and proof['paths']==44 and proof['enabled_rewrites']==36
    assert proof['reader_paths']==88 and proof['founder_acquisitions']==2


@pytest.mark.parametrize('role',[0,1])
def test_all_classes(role):
    total=[]
    for quarter in system.LEVELS[role]:
        offsets=system.members(role,quarter)
        assert len(offsets)>0 and all(audit.geometry(role,d)==quarter and np.any(d) for d in offsets)
        assert offsets.tolist()==sorted(offsets.tolist());total.extend(map(tuple,offsets))
    assert len(total)==len(set(total))==255 and (0,0) not in total
    assert len(system.members(role,4))==(15 if role==0 else 31)


def test_schedule_independence(monkeypatch):
    monkeypatch.setattr(system,'generate_founders',forbidden);monkeypatch.setattr(system,'simulate',forbidden)
    schedule=run.address_schedule()
    assert schedule['outcome_access'] is False and schedule['blocks']==list(range(91000,91016))
    for i in system.BLOCKS:
        for l in range(4):
            for n in (0,1):
                for ci,(r,k) in enumerate(system.CASES):
                    np.testing.assert_array_equal(schedule['shifts'][str(i)][l][n][ci],audit.address(i,l,n,r,k))
    assert system.CASES==audit.CASES and len(system.CASES)==22


def test_matching(panel):
    raw=panel['raw']
    for r in (0,1):
        zero=system.CASES.index((r,'zero'))
        for ci,(role,kind) in enumerate(system.CASES):
            if role==r and kind!='read_off':np.testing.assert_array_equal(raw['read_states'][:,ci],raw['read_states'][:,zero])
            if role==r and kind.startswith('q'):np.testing.assert_array_equal(raw['write_states'][:,ci,:2],raw['write_states'][:,zero,:2])
    assert not np.array_equal(raw['terminal_states'][0,0,0],raw['read_states'][0,0,0])
    assert not np.array_equal(raw['read_states'][0,0,0],raw['read_states'][1,0,0])


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
    ('family_supplied_to_address_rule',False),('writer_receives_target_labels',True),('terminal_is_fresh',False),('guide_refitted',True)])
def test_metadata_corruption(panel,key,value):
    meta=copy.deepcopy(panel['meta']);meta['trials'][0][key]=value
    with pytest.raises((AssertionError,ValueError)):audit.check_life(panel['raw'],meta,False)


def test_condition_order(panel):
    raw=panel['raw'];repeat,meta=system.simulate(system.DISPOSABLE,0,0,raw['founder_packets'],raw['guide'],tuple(reversed(system.CASES)))
    for k,v in repeat.items():np.testing.assert_array_equal(v,raw[k][0])
    assert meta==panel['meta']['trials'][0]
    with pytest.raises(ValueError):system.simulate(system.DISPOSABLE,0,0,raw['founder_packets'],raw['guide'],system.CASES[:-1])


@pytest.mark.parametrize('index,life,noise',[(90000,0,0),(91016,0,0),(True,0,0),(91000,4,0),(91000,False,0),(91000,0,2),(91000,0,False)])
def test_namespace_guard(index,life,noise):
    with pytest.raises(ValueError):system.rng(index,life,noise,'read')


def test_fresh_founder_namespace(panel):
    assert set(system.BLOCKS).isdisjoint(heldout_system.TISSUES) and system.TAG!=heldout_system.TAG
    for phase in system.PHASES:
        x=system.rng(91000,0,0,phase).normal(size=16)
        assert not np.array_equal(x,system.rng(91000,0,1,phase).normal(size=16))
        assert not np.array_equal(x,system.old.generator(heldout_system.TAG,91000,0,'noise0:'+phase).normal(size=16))
    assert panel['meta']['founder']['tag']==system.TAG
    with pytest.raises(ValueError):system.rng(91000,0,0,'unknown')


def test_zero_shift_bridge(panel):
    raw=panel['raw'];ctx=system.old.context(system.DISPOSABLE);ci=system.CASES.index((1,'zero'))
    writes,_=system.old.write_streams(raw['read_states'][0,ci,-1],ctx,system.rng(system.DISPOSABLE,0,0,'write'),
        'translated',np.array([0,0],np.int64),system.CONFIG)
    np.testing.assert_array_equal(writes,raw['write_states'][0,ci])


def test_schema_roundtrip(panel):
    meta=run.io.read_json(panel['directory']/'meta.json');raw=run.io.load_npz(panel['directory']/'raw.npz')
    assert 'read_times' not in meta['config'] and meta['config']['steps']==300
    assert isinstance(meta['host']['tissue']['strict_band'],list)
    assert audit.check_life(raw,meta,False)['paths']==44


def test_external_roundtrip(panel):
    raw=run.io.load_npz(panel['directory']/'raw.npz')
    for k in raw:np.testing.assert_array_equal(raw[k],panel['raw'][k])
    with pytest.raises(FileExistsError):run.io.write_npz(panel['directory']/'raw.npz',raw,run.ROOT)


def test_no_source_mutation(panel):
    raw=panel['raw'];founders=raw['founder_packets'].copy();guide=raw['guide'].copy()
    for ci,(role,kind) in enumerate(system.CASES):
        for n in (0,1):np.testing.assert_array_equal(raw['incoming'][n,ci],founders[role])
        if kind=='copy':np.testing.assert_array_equal(raw['outgoing'][:,ci],np.repeat(founders[role,None],2,axis=0))
        if kind=='write_off':assert not np.count_nonzero(raw['outgoing'][:,ci])
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
        block={p+'_values':np.zeros((4,2,22,t,2)) for p,t in (('read',5),('write',4),('terminal',4))}
        block['record_values']=np.zeros((4,2,22,2));block['shift']=np.zeros((4,2,22,2),np.int64)
        for ci,(role,kind) in enumerate(system.CASES):
            value=.2 if kind not in ('read_off','write_off') else 0.
            if kind=='q4' and role==1:value+=effect
            block['terminal_values'][:,:,ci,-1,0]=value
            block['record_values'][:,:,ci,1]=.4+(.4 if kind=='q4' else 0.)
        blocks.append(block)
        records.append(dict(lives=[dict(trials=[dict(paths=[dict(terminal_selector=dict(inferred_family=r)) for r,k in system.CASES]) for n in (0,1)]) for l in range(4)]))
    return blocks,records


def test_complete_summary(monkeypatch):
    blocks,records=synthetic(.125);s=analysis.summarize(blocks,records)
    monkeypatch.setattr(analysis,'summarize',forbidden);monkeypatch.setattr(analysis,'stats',forbidden)
    assert independent.check(s,blocks,records)['passes']
    assert s['label']=='B_COMPATIBLE_DESCENDANT_BENEFIT' and s['primary']['mean']==.125
    s['primary']['mean']+=.01
    with pytest.raises(AssertionError):independent.check(s,blocks,records)


def test_primary_not_shape():
    b,m=synthetic(-.0625);s=analysis.summarize(b,m)
    assert s['label']=='B_COMPATIBLE_DESCENDANT_HARM' and s['primary']['mean']==-.0625
    assert next(v for v in s['contrasts'] if (v['role'],v['condition'])==(1,'q4'))['metrics']['outgoing_shape']['mean']>0
    assert independent.check(s,b,m)['passes']


def test_constant_unresolved():
    b,m=synthetic();s=analysis.summarize(b,m)
    assert s['label']=='B_COMPATIBLE_EFFECT_UNRESOLVED' and s['primary']['pointwise_block_bootstrap_95']==[0.,0.]
    assert s['equivalence_test'] is False and independent.check(s,b,m)['passes']


def test_source_closure():
    files=run.source_closure();assert len(files)>1370
    assert all(system.dev.WS/p in files for p in run.SCIENCE)
    assert not any(p.name=='README.md' and p.parent==system.dev.WS/'compatible-feedback' for p in files)


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
    rd,wr=os.pipe();monkeypatch.setenv('D144_READY_FD',str(wr));run.signal_ready('execute')
    try:assert json.loads(os.read(rd,4096))==dict(stage='execute',pid=os.getpid(),status='STARTED')
    finally:os.close(rd)


def test_no_automatic_successor():
    assert run.contract()['automatic_successor'] is False and run.contract()['automatic_polling'] is False
    assert 'execute(' not in inspect.getsource(run.benchmark) and 'prepare(' not in inspect.getsource(run.benchmark)
    assert 'detach(' not in inspect.getsource(run.execute)


def test_main_barrier(monkeypatch,tmp_path):
    monkeypatch.setattr(system,'simulate_life',forbidden)
    with pytest.raises(ValueError):run.worker(tmp_path,91000)
    monkeypatch.setattr(run,'barrier',lambda *a:(_ for _ in ()).throw(RuntimeError('no seal')))
    with pytest.raises(RuntimeError):run.worker(tmp_path,91000,tmp_path,'not-a-manifest')
    assert run.contract()['all_addresses_before_any_founders'] is True


def test_failure_receipt(tmp_path,monkeypatch):
    monkeypatch.setattr(run,'preflight',lambda:None);monkeypatch.setattr(run,'frozen',lambda:{'test_proof':{'benchmark_forecast':0}})
    directory=tmp_path/'failed_benchmark';monkeypatch.setattr(run,'benchmark_dir',lambda:directory)
    monkeypatch.setattr(run,'worker',lambda *a:(_ for _ in ()).throw(RuntimeError('synthetic failure')))
    with pytest.raises(RuntimeError):run.benchmark()
    assert (directory/'FAILED.json').exists() and not (directory/'score_fixture.json').exists()
