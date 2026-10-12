"""D147 disposable readouts, exact-source bridges and fixed independent inference."""
import copy
import inspect
import json
import os
import subprocess
import sys
import numpy as np
import pytest
from l20_extension1 import stopping_system as system,stopping_audit as audit
from l20_extension1 import stopping_analysis as analysis,stopping_analysis_check as independent
from l20_extension1 import stopping_run as run


def forbidden(*a,**k): raise AssertionError('forbidden dynamics/source access')


@pytest.fixture(scope='module')
def panel(tmp_path_factory):
    raw,meta=system.load_source(system.DISPOSABLE)
    source={k:v[0] for k,v in raw.items()};sm=meta['lives'][0]
    before=run.io.hashes(system.source_paths(system.DISPOSABLE))
    new,entry=system.simulate_life(system.DISPOSABLE,0,source,sm)
    entry['replay']=audit.check_life(new,entry,source,sm,True)
    directory=tmp_path_factory.mktemp('stopping_disposable')
    run.io.write_npz(directory/'raw.npz',new,run.ROOT);run.io.write_json(directory/'meta.json',entry,run.ROOT)
    return dict(raw=new,meta=entry,source=source,source_meta=sm,directory=directory,source_hashes=before)


def checked(panel,replay=False,raw=None,meta=None,source=None):
    return audit.check_life(panel['raw'] if raw is None else raw,panel['meta'] if meta is None else meta,
        panel['source'] if source is None else source,panel['source_meta'],replay)


def test_full_disposable_life(panel):
    p=panel['meta']['replay']
    assert p['full_new_dynamics_replayed'] and p['labelled_cells']==96
    assert p['new_assays']==p['replayed_new_assays']==8 and p['reused_labels']==88
    assert p['replayed_existing_assays']==p['new_founders']==p['new_upstream_dynamics']==0


def test_source_bridges(panel):
    system.validate_bridges(panel['source']);audit.source_bridges(panel['source'])
    assert system.CASES==audit.CASES and len(system.CASES)==16
    for r in (0,1):
        for t in (1000,1300):
            for k in system.KINDS:
                for g in (1,2,3): assert system.reuse_kind(t,k,g)==audit.endpoint_kind(t,k,g)


def test_reuse_accounting():
    new=sum(system.reuse_kind(t,k,g) is None for r,t,k in system.CASES for g in (1,2,3))
    assert new==4 and new*2*4*16==512
    assert len(system.CASES)*3*2*4*16==6144
    assert run.contract()['reused_labels']==5632 and run.contract()['independent_blocks']==16


def test_matching(panel):
    raw=panel['raw']
    for ci in range(16): np.testing.assert_array_equal(raw['terminal_states'][:,ci,:,0],raw['terminal_states'][:,0,:,0])
    assert not np.array_equal(raw['terminal_states'][0,0,0,0],raw['terminal_states'][1,0,0,0])
    for g in (1,2): assert not np.array_equal(raw['terminal_states'][0,0,g,0],raw['terminal_states'][0,0,g-1,0])
    assert panel['meta']['physics_namespace']==system.source.TAG!=system.TAG


def test_independent_replay(panel,monkeypatch):
    for name in ('simulate_life','readout','emitted','validate_bridges','reuse_kind'):monkeypatch.setattr(system,name,forbidden)
    for name in ('read_selected','write_streams','route','record'):monkeypatch.setattr(system.old,name,forbidden)
    assert checked(panel,True)['replayed_new_assays']==8


def test_saved_no_dynamics(panel,monkeypatch):
    monkeypatch.setattr(audit.physics,'step',forbidden)
    assert checked(panel)['replayed_new_assays']==0


@pytest.mark.parametrize('key',['packet','terminal_packet','scores','terminal_states','terminal_values','record_values','founder_packets','guide'])
def test_corruption(panel,key):
    raw=panel['raw'].copy();raw[key]=raw[key].copy()
    if raw[key].dtype==np.uint8: raw[key].flat[0]^=1
    else: raw[key].flat[0]+=1
    with pytest.raises((AssertionError,ValueError)):checked(panel,raw=raw)


@pytest.mark.parametrize('key,value',[('tag','other'),('physics_namespace',system.TAG),('source_run','wrong'),
    ('new_assays',96),('new_founders',1),('source_state_given_to_reader',True),('assay_enters_lineage',True),
    ('guide_refitted',True),('new_independent_noise',True),('same_extended_history',False)])
def test_metadata_corruption(panel,key,value):
    meta=copy.deepcopy(panel['meta']);meta[key]=value
    with pytest.raises((AssertionError,ValueError)):checked(panel,meta=meta)


@pytest.mark.parametrize('key,value',[('stop',999),('write_checkpoint',4),('new_assay',False),
    ('endpoint_source_kind','base'),('assay_steps',600),('carrier_bytes',64)])
def test_cell_metadata_corruption(panel,key,value):
    meta=copy.deepcopy(panel['meta']);meta['cells'][0][0][1][key]=value
    with pytest.raises((AssertionError,ValueError)):checked(panel,meta=meta)


def test_condition_order(panel):
    raw,meta=system.simulate_life(system.DISPOSABLE,0,panel['source'],panel['source_meta'],tuple(reversed(system.CASES)))
    for k,v in raw.items():np.testing.assert_array_equal(v,panel['raw'][k])
    assert meta=={k:v for k,v in panel['meta'].items() if k!='replay'}
    with pytest.raises(ValueError):system.simulate_life(system.DISPOSABLE,0,panel['source'],panel['source_meta'],system.CASES[:-1])


@pytest.mark.parametrize('index,life',[(93016,0),(92000,0),(True,0),(93000,4),(93000,False)])
def test_namespace_guard(index,life):
    with pytest.raises(ValueError):system.source.validate(index,life)
    with pytest.raises(ValueError):system.reuse_kind(999,'intact',1)
    with pytest.raises(ValueError):system.reuse_kind(1000,'other',1)
    with pytest.raises(ValueError):system.reuse_kind(1000,'intact',True)


def test_existing_endpoints(panel):
    raw,src=panel['raw'],panel['source']
    for ci,(r,t,k) in enumerate(system.CASES):
        for gi in range(3):
            name=system.reuse_kind(t,k,gi+1)
            if name is not None:
                si=audit.index_of(r,name)
                np.testing.assert_array_equal(raw['terminal_states'][:,ci,gi],src['terminal_states'][:,si,gi])
                np.testing.assert_array_equal(raw['packet'][:,ci,gi],src['outgoing'][:,si,gi])


@pytest.mark.parametrize('generation',[0,1,2])
def test_source_prefix_corruption(panel,generation):
    source=panel['source'].copy();source['write_states']=source['write_states'].copy()
    source['write_states'][0,2,generation,4,0,0,0]+=1
    with pytest.raises(AssertionError):system.validate_bridges(source)
    with pytest.raises(AssertionError):checked(panel,source=source)


def test_checkpoint_not_theta(panel):
    for r in (0,1):
        for t,wi in ((1000,3),(1300,4)):
            si=audit.index_of(r,'write')
            for g in (1,2,3):
                ref=panel['source']['write_states'][0,si,g-1,wi,2]
                theta=panel['source']['write_states'][0,si,g-1,wi,3]
                emitted=system.emitted(panel['source'],0,r,t,'intact',g)
                assert emitted==system.old.encode(system.old.record(ref))
                assert emitted!=system.old.encode(theta)


def test_constant_assay(panel):
    assert panel['raw']['terminal_states'].shape==(2,16,3,4,3,16,16)
    for trial in panel['meta']['cells']:
        for case in trial:
            for cell in case: assert cell['assay_steps']==300 and cell['assay_enters_lineage'] is False
    assert tuple(system.CONFIG.times)==(0,1,100,300)


def test_same_history_not_new_lineage(panel,monkeypatch):
    monkeypatch.setattr(system.old,'write_streams',forbidden)
    monkeypatch.setattr(system.source,'generate_founders',forbidden)
    raw,_=system.simulate_life(system.DISPOSABLE,0,panel['source'],panel['source_meta'])
    for k,v in raw.items():np.testing.assert_array_equal(v,panel['raw'][k])
    assert panel['meta']['new_upstream_dynamics']==0 and run.contract()['fresh_cohort'] is False


def test_assay_isolation(panel,monkeypatch):
    original=system.readout
    def altered(*args,**kwargs):
        states,meta=original(*args,**kwargs)
        return states+.007,meta
    monkeypatch.setattr(system,'readout',altered)
    raw,_=system.simulate_life(system.DISPOSABLE,0,panel['source'],panel['source_meta'])
    for k in ('packet','terminal_packet','scores','record_values','founder_packets','guide'):
        np.testing.assert_array_equal(raw[k],panel['raw'][k])
    for ci,(r,t,k) in enumerate(system.CASES):
        for gi in range(3):
            same=np.array_equal(raw['terminal_states'][:,ci,gi],panel['raw']['terminal_states'][:,ci,gi])
            assert same==(system.reuse_kind(t,k,gi+1) is not None)


def test_new_assay_replay_corruption(panel):
    raw=panel['raw'].copy();raw['terminal_states']=raw['terminal_states'].copy();raw['terminal_values']=raw['terminal_values'].copy()
    # Internally consistent changed observation can pass a saved-only audit but not a physics replay.
    raw['terminal_states'][0,0,1,-1,2,0,0]+=.007
    raw['terminal_values'][0,0,1]=system.source.observations(raw['terminal_states'][0,0,1],0)
    assert checked(panel,raw=raw)['replayed_new_assays']==0
    with pytest.raises(AssertionError):checked(panel,True,raw=raw)


def test_no_source_mutation(panel):
    assert run.io.hashes(system.source_paths(system.DISPOSABLE))==panel['source_hashes']
    assert all(not v.flags.writeable for v in panel['source'].values())
    assert not any(np.shares_memory(v,panel['source'][k]) for k,v in panel['raw'].items() if k in panel['source'])


def test_external_roundtrip(panel):
    raw=run.io.load_npz(panel['directory']/'raw.npz')
    for k,v in raw.items():np.testing.assert_array_equal(v,panel['raw'][k])
    with pytest.raises(FileExistsError):run.io.write_npz(panel['directory']/'raw.npz',raw,run.ROOT)


def test_schema_roundtrip(panel):
    raw=run.io.load_npz(panel['directory']/'raw.npz');meta=run.io.read_json(panel['directory']/'meta.json')
    assert isinstance(meta['host']['tissue']['strict_band'],list)
    assert checked(panel,raw=raw,meta=meta)['labelled_cells']==96


def test_sixteen_block_normalization():
    x=np.broadcast_to(np.arange(16,dtype=float)[:,None,None],(16,4,2));draws=np.tile(np.arange(16),(10000,1))
    a=analysis.stats(x,draws);b=independent.stats(x,draws)
    assert a['mean']==7.5 and a['pointwise_block_bootstrap_95']==[7.5,7.5]
    audit.physics.nested(a,b)
    with pytest.raises(ValueError):analysis.stats(x[:8],draws)


def test_block_bootstrap():
    x=np.arange(128,dtype=float).reshape(16,4,2)/128;draws=np.zeros((10000,16),int)
    a=analysis.stats(x,draws);expected=x[0].sum()/8
    assert a['pointwise_block_bootstrap_95']==[expected,expected]
    audit.physics.nested(a,independent.stats(x,draws))


def synthetic(effect=0.):
    blocks=[];records=[]
    for _ in range(16):
        b=dict(terminal_values=np.zeros((4,2,16,3,4,2)),record_values=np.zeros((4,2,16,3,4)))
        for ci,(r,t,k) in enumerate(system.CASES):
            value=.25 if k in ('intact','copy') else 0.
            if (r,t,k)==(1,1300,'intact'):value+=effect
            b['terminal_values'][:,:,ci,:,-1,0]=value
            b['record_values'][:,:,ci,:,0]=.8 if t==1300 else .4
        blocks.append(b)
        records.append(dict(lives=[dict(cells=[[[dict(terminal_selector=dict(inferred_family=r)) for g in range(3)]
            for r,t,k in system.CASES] for n in (0,1)]) for l in range(4)]))
    return blocks,records


def test_complete_summary(monkeypatch):
    b,m=synthetic(.125);s=analysis.summarize(b,m)
    monkeypatch.setattr(analysis,'summarize',forbidden);monkeypatch.setattr(analysis,'stats',forbidden)
    assert independent.check(s,b,m)['passes'] and s['primary']['mean']==.125
    assert s['label']=='B_CONTINUATION_FAVORED'
    assert [len(s[k]) for k in ('groups','stop_contrasts','copy_contrasts','controls','serial_changes')]==[48,24,12,36,16]
    s['primary']['mean']+=.01
    with pytest.raises(AssertionError):independent.check(s,b,m)


def test_primary_not_shape():
    b,m=synthetic(-.0625);s=analysis.summarize(b,m)
    assert s['primary']['mean']==-.0625 and s['label']=='B_STOPPING_FAVORED'
    c=next(c for c in s['stop_contrasts'] if (c['role'],c['condition'],c['generation'])==(1,'intact',3))
    assert c['metrics']['outgoing_shape']['mean']>0 and independent.check(s,b,m)['passes']


def test_late_primary():
    b,m=synthetic(.125);ci=system.CASES.index((1,1300,'intact'))
    for block in b:block['terminal_values'][:,:,ci,2,-1,0]=.25-.0625
    s=analysis.summarize(b,m)
    assert s['primary']['mean']==-.0625 and s['label']=='B_STOPPING_FAVORED'
    assert independent.check(s,b,m)['passes']


def test_control_gate_not_primary():
    b,m=synthetic(.125);ci=system.CASES.index((0,1000,'read_off'))
    for block in b:block['terminal_values'][:,:,ci,0,-1,0]=.9
    s=analysis.summarize(b,m)
    assert s['label']=='APPARATUS_NOT_QUALIFIED' and s['primary_interval_classification']=='B_CONTINUATION_FAVORED'
    assert s['primary']['mean']==.125 and independent.check(s,b,m)['passes']


def test_constant_unresolved():
    b,m=synthetic();s=analysis.summarize(b,m)
    assert s['label']=='B_STOPPING_DIFFERENCE_UNRESOLVED' and s['primary']['pointwise_block_bootstrap_95']==[0.,0.]
    assert s['equivalence_test'] is False and independent.check(s,b,m)['passes']


def test_metric_threshold():
    t=system.dev.targets()[1]
    for magnitude in (.2,np.nextafter(.2,1.)):
        v=magnitude*t;a=system.dev.terminal_features(v,1)[0];b=audit.metrics.terminal_features(v,1)[0]
        assert a==b and (a==0 if magnitude==.2 else a==.5)


def test_cell_plan_no_dynamics(monkeypatch):
    monkeypatch.setattr(system,'load_source',forbidden);monkeypatch.setattr(system,'simulate_life',forbidden)
    plan=run.cell_plan()
    assert len(plan['cells'])==48 and len(plan['source_files'])==16 and plan['new_outcome_access'] is False
    assert plan['source_outcomes_already_observed'] is True


def test_source_closure():
    paths=run.source_closure()
    assert len(paths)>=1580 and all(system.dev.WS/p in paths for p in run.SCIENCE)
    assert system.dev.WS/'phase-budget/SAVED_STATE_REVIEW_V1.md' in paths
    assert system.dev.WS/'stopping-time/README.md' not in paths


def test_resource_guards(monkeypatch):
    assert len(run.preflight())<=6 and run.ALLOWANCE==1024**3
    monkeypatch.setenv('OMP_NUM_THREADS','2')
    with pytest.raises((RuntimeError,AssertionError)):run.preflight()


def test_detached_guard(monkeypatch):
    monkeypatch.delenv(run.DETACHED_ENV,raising=False)
    with pytest.raises(RuntimeError):run.detached_guard(True)
    run.detached_guard(False)
    assert 'select.select([ready_read], [], [], 55)' in inspect.getsource(run.detach)
    assert 'child.poll' not in inspect.getsource(run.detach)


def test_startup_handshake(monkeypatch):
    rd,wr=os.pipe();monkeypatch.setenv('D147_READY_FD',str(wr));run.signal_ready('execute')
    try:assert json.loads(os.read(rd,4096))==dict(stage='execute',pid=os.getpid(),status='STARTED')
    finally:os.close(rd)


def test_no_automatic_successor():
    c=run.contract();assert not c['automatic_polling'] and not c['automatic_retry'] and not c['automatic_successor']
    assert 'execute(' not in inspect.getsource(run.benchmark) and 'prepare(' not in inspect.getsource(run.benchmark)
    assert 'detach(' not in inspect.getsource(run.execute)


def test_main_barrier(monkeypatch,tmp_path):
    monkeypatch.setattr(system,'simulate_life',forbidden)
    with pytest.raises(ValueError):run.worker(tmp_path,93000)
    monkeypatch.setattr(run,'barrier',lambda *a:(_ for _ in ()).throw(RuntimeError('no seal')))
    with pytest.raises(RuntimeError):run.worker(tmp_path,93000,tmp_path,'bad')
    assert run.contract()['cell_plan_before_new_main_assays'] is True


def test_cold_benchmark_audit_initializes():
    code="""from l20_extension1 import stopping_run as r
def stop_after_preflight():
    import voltage_web
    assert r.system.old.context(514246)['api'] is not None
    raise LookupError('cold initialization checked')
r.frozen=stop_after_preflight
try:r.benchmark_audit()
except LookupError as e:
    assert str(e)=='cold initialization checked'
    print('cold initialization checked')
else:raise AssertionError('sentinel not reached')
"""
    p=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True,timeout=30)
    assert p.returncode==0,(p.stdout,p.stderr)
    assert 'cold initialization checked' in p.stdout


def test_failure_receipt(tmp_path,monkeypatch):
    monkeypatch.setattr(run,'preflight',lambda:None);monkeypatch.setattr(run,'frozen',lambda:{'test_proof':{'benchmark_forecast':0}})
    directory=tmp_path/'failed_benchmark';monkeypatch.setattr(run,'benchmark_dir',lambda:directory)
    monkeypatch.setattr(run,'worker',lambda *a:(_ for _ in ()).throw(RuntimeError('synthetic failure')))
    with pytest.raises(RuntimeError):run.benchmark()
    assert (directory/'FAILED.json').exists() and not (directory/'score_fixture.json').exists()
