"""D149 full disposable readers, adversarial algebra and statistical qualification."""
import copy
import inspect
import json
import os
import subprocess
import sys
import numpy as np
import pytest
from l20_extension1 import component_system as system,component_audit as audit
from l20_extension1 import component_analysis as analysis,component_analysis_check as independent
from l20_extension1 import component_run as run


def forbidden(*args,**kwargs):raise AssertionError('forbidden dynamics/source/model access')


@pytest.fixture(scope='module')
def panel(tmp_path_factory):
    sb,sm=system.load_source(system.DISPOSABLE);src={k:v[0] for k,v in sb.items()}
    before=run.io.hashes(system.source_paths(system.DISPOSABLE))
    raw,meta=system.simulate_life(system.DISPOSABLE,0,src,sm['lives'][0])
    meta['replay']=audit.check_life(raw,meta,src,sm['lives'][0],True)
    directory=tmp_path_factory.mktemp('component_disposable')
    run.io.write_npz(directory/'raw.npz',raw,run.ROOT);run.io.write_json(directory/'meta.json',meta,run.ROOT)
    return dict(raw=raw,meta=meta,source=src,source_meta=sm['lives'][0],
        source_block=sb,block_meta=sm,directory=directory,source_hashes=before)


def checked(panel,replay=False,raw=None,meta=None):
    return audit.check_life(panel['raw'] if raw is None else raw,panel['meta'] if meta is None else meta,
        panel['source'],panel['source_meta'],replay)


def test_full_disposable_life(panel):
    p=panel['meta']['replay']
    assert p['full_new_dynamics_replayed'] and p['labelled_cells']==192 and p['untouched']==48
    assert 0<p['new_assays']<=144 and p['replayed_new_assays']==p['new_assays']
    assert p['reused_labels']+p['new_assays']==192 and p['replayed_existing_assays']==0
    assert p['invariant_max_abs']<=1e-12 and p['terminal_max_abs']<=1e-10


@pytest.mark.parametrize('role',[0,1])
@pytest.mark.parametrize('seed',[0,1,37,999])
def test_algebra(role,seed):
    f=np.random.default_rng(seed).normal(size=(16,16))*.3+.07;p=system.old.encode(f)
    edits,detail=system.edit_packets(p,role)
    for e,candidate in edits.items():
        value,d=audit.expected_edit(p,role,e)
        np.testing.assert_allclose(system.old.decode(candidate),value,atol=1e-12,rtol=0)
        audit.physics.nested(detail,d);audit.invariants(p,candidate,role,e,d)


@pytest.mark.parametrize('role',[0,1])
@pytest.mark.parametrize('kind',['zero','constant','own','competing','residual','near_zero_residual','near_zero_competing'])
def test_degenerate(role,kind):
    templates=system.dev.targets();q=np.outer(np.where(np.arange(16)<8,1.,-1.),np.where(np.arange(16)<8,1.,-1.))
    f={'zero':np.zeros((16,16)),'constant':np.full((16,16),.3),'own':templates[role]*.3,
       'competing':templates[1-role]*.3,'residual':q*.3,
       'near_zero_residual':templates[1-role]*.3+q*1e-14,
       'near_zero_competing':templates[1-role]*1e-14+q*.3}[kind]
    p=system.old.encode(f);edits,d=system.edit_packets(p,role)
    assert d['degenerate'] and d['dose_rms']==0 and all(v==p for v in edits.values())
    for e in system.EDITS:audit.invariants(p,p,role,e,audit.expected_edit(p,role,e)[1])


def test_equal_dose():
    p=system.old.encode(np.random.default_rng(2).normal(size=(16,16)))
    edits,d=system.edit_packets(p,1);f=system.old.decode(p)
    distances=[system.rms(system.old.decode(edits[e])-f) for e in system.EDITS[1:]]
    np.testing.assert_allclose(distances,d['dose_rms'],atol=1e-12,rtol=0)
    for e in ('sham_plus','sham_minus'):
        np.testing.assert_allclose(system.parts(system.old.decode(edits[e]),1)[2],system.parts(f,1)[2],atol=1e-12,rtol=0)


def test_walsh_fallback():
    t=system.dev.targets();h=np.where(np.arange(16)<8,1.,-1.)
    p=system.old.encode(.1*t[0]+.2*t[1]+.3*np.outer(h,h))
    edits,d=system.edit_packets(p,1)
    assert d['q_seed']==1
    for e,c in edits.items():audit.invariants(p,c,1,e,audit.expected_edit(p,1,e)[1])


@pytest.mark.parametrize('ratio',[1e-11,1e-6,1.,1e6,1e11])
def test_conditioned_extremes(ratio):
    t=system.dev.targets();h=np.where(np.arange(16)<8,1.,-1.)
    C,R=(.1*ratio,.1) if ratio<1 else (.1,.1/ratio)
    p=system.old.encode(.1*t[1]+C*t[0]+R*np.outer(h,h))
    values,d=system.edit_packets(p,1)
    for e,v in values.items():
        expected,_=audit.expected_edit(p,1,e)
        np.testing.assert_allclose(system.old.decode(v),expected,atol=1e-12,rtol=0)


def test_matching(panel):
    a=panel['raw']
    for ci in range(32):np.testing.assert_array_equal(a['terminal_states'][:,ci,:,0],a['terminal_states'][:,0,:,0])
    assert not np.array_equal(a['terminal_states'][0,0,0,0],a['terminal_states'][1,0,0,0])
    assert system.PHYSICS_TAG==system.source.PHYSICS_TAG!=system.TAG


def test_saved_no_dynamics(panel,monkeypatch):
    monkeypatch.setattr(audit.physics,'step',forbidden)
    assert checked(panel)['replayed_new_assays']==0


@pytest.mark.parametrize('key,value',[('tag','old'),('physics_namespace',system.TAG),('source_run','wrong'),
    ('source_state_given_to_reader',True),('assay_enters_lineage',True),('new_founders',1),
    ('new_independent_noise',True),('guide_refitted',True),('analyst_supplied_edit',False),('rerouted_after_edit',True)])
def test_metadata_corruption(panel,key,value):
    m=copy.deepcopy(panel['meta']);m[key]=value
    with pytest.raises((AssertionError,ValueError)):checked(panel,meta=m)


@pytest.mark.parametrize('key,value',[('edit','bad'),('forward_shift',[4,5]),('new_assay',True),
    ('source_mode','new_assay'),('edited_sha256','fake'),('source_case',99),('assay_steps',600),('dose_rms',99)])
def test_cell_corruption(panel,key,value):
    m=copy.deepcopy(panel['meta']);m['cells'][0][0][0][key]=value
    with pytest.raises((AssertionError,ValueError)):checked(panel,meta=m)


@pytest.mark.parametrize('index,life',[(93016,0),(92000,0),(True,0),(93000,4),(93000,False)])
def test_namespace_guard(index,life):
    with pytest.raises(ValueError):system.validate(index,life)


def test_independent_plan(panel,monkeypatch):
    plan=system.block_plan(system.DISPOSABLE,panel['source_block'],panel['block_meta'])
    assert plan['untouched']==192 and plan['labelled_cells']==768 and 0<plan['new_assays']<=576
    p,q,s=system.cell(panel['source'],panel['source_meta'],0,1,'attenuate','intact',2)
    monkeypatch.setattr(system,'edit_packets',forbidden);monkeypatch.setattr(system,'cell',forbidden)
    assert audit.check_candidate(q,s,panel['source'],panel['source_meta'],0,1,'attenuate','intact',2)[0]==p
    s=copy.deepcopy(s);s['edited_sha256']='bad'
    with pytest.raises(AssertionError):audit.check_candidate(q,s,panel['source'],panel['source_meta'],0,1,'attenuate','intact',2)


def test_no_source_mutation(panel):
    assert run.io.hashes(system.source_paths(system.DISPOSABLE))==panel['source_hashes']
    assert all(not v.flags.writeable for v in panel['source'].values())


def test_same_history_not_new_lineage(panel,monkeypatch):
    monkeypatch.setattr(system.old,'write_streams',forbidden)
    monkeypatch.setattr(system.source.source.source,'generate_founders',forbidden)
    raw,_=system.simulate_life(system.DISPOSABLE,0,panel['source'],panel['source_meta'])
    for k,v in raw.items():np.testing.assert_array_equal(v,panel['raw'][k])
    assert not run.contract()['fresh_cohort'] and run.contract()['new_upstream_dynamics']==0


def test_no_reroute(panel,monkeypatch):
    monkeypatch.setattr(system.old,'route',forbidden);monkeypatch.setattr(system.old,'record',forbidden)
    raw,_=system.simulate_life(system.DISPOSABLE,0,panel['source'],panel['source_meta'])
    for k in ('terminal_packet','shift','terminal_states'):np.testing.assert_array_equal(raw[k],panel['raw'][k])


def test_assay_isolation(panel,monkeypatch):
    original=system.readout
    def altered(*a,**k):
        states,meta=original(*a,**k);return states+.007,meta
    monkeypatch.setattr(system,'readout',altered)
    raw,_=system.simulate_life(system.DISPOSABLE,0,panel['source'],panel['source_meta'])
    for k in ('packet','terminal_packet','shift','record_values','guide','founder_packets'):
        np.testing.assert_array_equal(raw[k],panel['raw'][k])
    assert not np.array_equal(raw['terminal_states'],panel['raw']['terminal_states'])


def test_threshold_boundary():
    t=system.dev.targets();v=t[1]*.2
    np.testing.assert_array_equal(independent.categories(v,1),0)
    v=t[1]*np.nextafter(.2,np.inf)
    np.testing.assert_array_equal(independent.categories(v,1),1)
    np.testing.assert_array_equal(independent.categories(v,0),2)


def test_transition_partition():
    before=np.tile(np.repeat(np.arange(3),3),15)[:128]
    after=np.tile(np.tile(np.arange(3),3),15)[:128]
    table,parts=independent.table_and_parts(before,after)
    np.testing.assert_array_equal(table,system.fields.transitions(after,before))
    np.testing.assert_array_equal(parts,system.fields.parts(table))


def set_score(block,ci,gi,count):
    role=system.CASES[ci][0];t=system.dev.targets();positions=np.flatnonzero((t[0]!=t[1]).ravel())
    v=np.zeros(256);v[positions[:count]]=.4*t[role].ravel()[positions[:count]]
    block['terminal_states'][:,:,ci,gi,:,0]=v.reshape(16,16)
    block['terminal_values'][:,:,ci,gi,:,0]=count/256


def synthetic(effect=0.):
    b=dict(terminal_values=np.zeros((4,2,32,3,4,4)),record_values=np.zeros((4,2,32,3,10)),
        terminal_states=np.zeros((4,2,32,3,4,3,16,16)))
    cells=[]
    for ci,(role,e,k) in enumerate(system.CASES):
        for gi in range(3):
            count=64 if k in ('intact','copy') else 0
            if (role,e,k,gi)==(1,'attenuate','intact',1):count+=int(round(effect*256))
            set_score(b,ci,gi,count)
        b['record_values'][:,:,ci,:,8]=.9 if e=='attenuate' else .1
        mode='untouched' if e=='untouched' else 'identical_bytes'
        cells.append([dict(degenerate=True,new_assay=False,source_mode=mode) for _ in range(3)])
    meta=dict(lives=[dict(cells=[cells,cells]) for _ in range(4)])
    return [b]*16,[meta]*16


def test_complete_summary(monkeypatch):
    b,m=synthetic(.125);s=analysis.summarize(b,m)
    monkeypatch.setattr(analysis,'summarize',forbidden);monkeypatch.setattr(analysis,'contrasts',forbidden)
    assert independent.check(s,b,m)['passes'] and s['primary']['mean']==.125
    assert s['label']=='B_G2_ATTENUATION_FAVORED'
    assert [len(s[k]) for k in ('groups','comparisons','controls','copy_contrasts','transition_accounting')]==[96,24,72,24,72]
    s['primary']['mean']+=.01
    with pytest.raises(AssertionError):independent.check(s,b,m)


def test_primary_not_shape():
    b,m=synthetic(-.0625);s=analysis.summarize(b,m)
    assert s['primary']['mean']==-.0625 and s['label']=='B_G2_SHAMS_FAVORED'
    assert independent.check(s,b,m)['passes']


def test_primary_g2_not_g3():
    b,m=synthetic(.125);ci=system.CASES.index((1,'attenuate','intact'))
    set_score(b[0],ci,2,32);s=analysis.summarize(b,m)
    assert s['primary']['mean']==.125 and independent.check(s,b,m)['passes']


def test_control_gate_not_primary():
    b,m=synthetic(.125);ci=system.CASES.index((0,'untouched','read_off'))
    set_score(b[0],ci,0,100);s=analysis.summarize(b,m)
    assert s['label']=='APPARATUS_NOT_QUALIFIED' and s['primary_interval_classification']=='B_G2_ATTENUATION_FAVORED'
    assert s['primary']['mean']==.125 and independent.check(s,b,m)['passes']


def test_edited_controls_not_gate():
    b,m=synthetic(.125);ci=system.CASES.index((0,'attenuate','read_off'))
    set_score(b[0],ci,0,100);s=analysis.summarize(b,m)
    assert s['apparatus_qualified'] and not all(c['passes'] for c in s['controls'])
    assert independent.check(s,b,m)['passes']


def test_constant_unresolved():
    b,m=synthetic();s=analysis.summarize(b,m)
    assert s['label']=='B_G2_COMPONENT_DIFFERENCE_UNRESOLVED' and s['primary']['pointwise_block_bootstrap_95']==[0.,0.]
    assert not s['equivalence_test'] and independent.check(s,b,m)['passes']


def test_source_closure():
    files=run.source_closure();assert len(files)>=1730
    assert all(system.dev.WS/p in files for p in run.SCIENCE)
    assert system.dev.WS/'packet-placement/SAVED_STATE_REVIEW_V1.md' in files
    assert system.dev.WS/'competing-component/README.md' not in files


def test_independent_replay(panel,monkeypatch):
    for name in ('simulate_life','readout','edit_packets','cell'):monkeypatch.setattr(system,name,forbidden)
    for name in ('read_selected','write_streams','route','record'):monkeypatch.setattr(system.old,name,forbidden)
    assert checked(panel,True)['replayed_new_assays']==panel['meta']['new_assays']

@pytest.mark.parametrize('key',['packet','terminal_packet','shift','terminal_states','terminal_values','record_values','guide','founder_packets'])
def test_corruption(panel,key):
    raw=panel['raw'].copy();raw[key]=raw[key].copy()
    if raw[key].dtype==np.uint8:raw[key].flat[0]^=1
    else:raw[key].flat[0]+=1
    with pytest.raises((AssertionError,ValueError)):checked(panel,raw=raw)

def test_condition_order(panel):
    raw,meta=system.simulate_life(system.DISPOSABLE,0,panel['source'],panel['source_meta'],tuple(reversed(system.CASES)))
    for k,v in raw.items():np.testing.assert_array_equal(v,panel['raw'][k])
    assert meta=={k:v for k,v in panel['meta'].items() if k!='replay'}
    with pytest.raises(ValueError):system.simulate_life(system.DISPOSABLE,0,panel['source'],panel['source_meta'],system.CASES[:-1])

def test_existing_endpoints(panel):
    for n in (0,1):
        for ci,case in enumerate(panel['meta']['cells'][n]):
            for gi,e in enumerate(case):
                if not e['new_assay']:
                    pi=e['source_case']
                    np.testing.assert_array_equal(panel['raw']['terminal_states'][n,ci,gi],panel['source']['terminal_states'][n,pi,gi])
                    np.testing.assert_array_equal(panel['raw']['terminal_packet'][n,ci,gi],panel['source']['terminal_packet'][n,pi,gi])

def test_constant_assay(panel):
    assert panel['raw']['terminal_states'].shape==(2,32,3,4,3,16,16)
    assert tuple(system.CONFIG.times)==(0,1,100,300)
    assert all(e['assay_steps']==300 for n in panel['meta']['cells'] for case in n for e in case)

def test_new_assay_replay_corruption(panel):
    n,ci,gi=next((n,ci,g) for n in (0,1) for ci,c in enumerate(panel['meta']['cells'][n]) for g,e in enumerate(c) if e['new_assay'])
    raw=panel['raw'].copy();raw['terminal_states']=raw['terminal_states'].copy();raw['terminal_values']=raw['terminal_values'].copy()
    raw['terminal_states'][n,ci,gi,-1,2,0,0]+=.007
    raw['terminal_values'][n,ci,gi]=system.observation(raw['terminal_states'][n,ci,gi],system.CASES[ci][0])
    assert checked(panel,raw=raw)['replayed_new_assays']==0
    with pytest.raises(AssertionError):checked(panel,True,raw=raw)

def test_external_roundtrip(panel):
    for k,v in run.io.load_npz(panel['directory']/'raw.npz').items():np.testing.assert_array_equal(v,panel['raw'][k])
    with pytest.raises(FileExistsError):run.io.write_npz(panel['directory']/'raw.npz',panel['raw'],run.ROOT)

def test_schema_roundtrip(panel):
    meta=run.io.read_json(panel['directory']/'meta.json');raw=run.io.load_npz(panel['directory']/'raw.npz')
    assert isinstance(meta['host']['tissue']['strict_band'],list)
    assert checked(panel,raw=raw,meta=meta)['labelled_cells']==192

def test_sixteen_block_normalization():
    x=np.broadcast_to(np.arange(16,dtype=float)[:,None,None],(16,4,2));draws=np.tile(np.arange(16),(10000,1))
    a=analysis.stats(x,draws);assert a['mean']==7.5 and a['pointwise_block_bootstrap_95']==[7.5,7.5]
    audit.physics.nested(a,independent.stats(x,draws))
    with pytest.raises(ValueError):analysis.stats(x[:8],draws)

def test_block_bootstrap():
    x=np.arange(128,dtype=float).reshape(16,4,2)/128;draws=np.zeros((10000,16),int)
    s=analysis.stats(x,draws);assert s['pointwise_block_bootstrap_95']==[x[0].sum()/8]*2
    audit.physics.nested(s,independent.stats(x,draws))

def test_resource_guards(monkeypatch):
    assert len(run.preflight())<=6 and run.ALLOWANCE==2*1024**3
    monkeypatch.setenv('OMP_NUM_THREADS','2')
    with pytest.raises((RuntimeError,AssertionError)):run.preflight()

def test_detached_guard(monkeypatch):
    monkeypatch.delenv(run.DETACHED_ENV,raising=False)
    with pytest.raises(RuntimeError):run.detached_guard(True)
    run.detached_guard(False)
    assert 'select.select([ready_read], [], [], 55)' in inspect.getsource(run.detach)
    assert 'child.poll' not in inspect.getsource(run.detach)

def test_startup_handshake(monkeypatch):
    rd,wr=os.pipe();monkeypatch.setenv('D149_READY_FD',str(wr));run.signal_ready('execute')
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
    assert run.contract()['cell_plan_before_new_main_assays'] and run.contract()['cell_plan_in_freeze']

def test_budget_scale():
    assert run.work_scale(10,dict(max_block_new_assays=20))==2
    assert run.work_scale(20,dict(max_block_new_assays=10))==1
    assert run.work_scale(0,dict(max_block_new_assays=3))==3
    assert run.work_scale(0,dict(max_block_new_assays=0))==1

def test_cold_benchmark_audit_initializes():
    code="""from l20_extension1 import component_run as r
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

