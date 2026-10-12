"""D148 crossed fresh-readout and saved-history qualification, disposable only."""
import copy
import inspect
import json
import os
import subprocess
import sys
import numpy as np
import pytest
from l20_extension1 import placement_system as system,placement_audit as audit
from l20_extension1 import placement_analysis as analysis,placement_analysis_check as independent
from l20_extension1 import placement_history as history,placement_history_check as history_check
from l20_extension1 import placement_run as run


def forbidden(*args,**kwargs):raise AssertionError('forbidden dynamics/source/model access')


@pytest.fixture(scope='module')
def panel(tmp_path_factory):
    sb,sm=system.load_source(system.DISPOSABLE);ub,um=system.source.load_source(system.DISPOSABLE)
    src={k:v[0] for k,v in sb.items()};up={k:v[0] for k,v in ub.items()}
    before=run.io.hashes((*system.source_paths(system.DISPOSABLE),*system.source.source_paths(system.DISPOSABLE)))
    raw,meta=system.simulate_life(system.DISPOSABLE,0,src,sm['lives'][0])
    meta['replay']=audit.check_life(raw,meta,src,sm['lives'][0],True)
    rows=history.extract_life(system.DISPOSABLE,0,src,sm['lives'][0],up,um['lives'][0])
    hp=history_check.check_life(rows,system.DISPOSABLE,0,src,sm['lives'][0],up,um['lives'][0])
    directory=tmp_path_factory.mktemp('placement_disposable')
    run.io.write_npz(directory/'raw.npz',raw,run.ROOT);run.io.write_json(directory/'meta.json',meta,run.ROOT)
    run.io.write_json(directory/'history.json',rows,run.ROOT)
    return dict(raw=raw,meta=meta,source=src,source_meta=sm['lives'][0],upstream=up,upstream_meta=um['lives'][0],
        source_block=sb,block_meta=sm,rows=rows,history_proof=hp,directory=directory,source_hashes=before)


def checked(panel,replay=False,raw=None,meta=None):
    return audit.check_life(panel['raw'] if raw is None else raw,panel['meta'] if meta is None else meta,
        panel['source'],panel['source_meta'],replay)


def test_full_disposable_life(panel):
    p=panel['meta']['replay']
    assert p['full_new_dynamics_replayed'] and p['labelled_cells']==192 and p['natural_diagonals']==96
    assert 0<p['new_assays']<=48 and p['replayed_new_assays']==p['new_assays']
    assert p['reused_labels']+p['new_assays']==192 and p['replayed_existing_assays']==0
    assert panel['history_proof']['history_rows']==4 and panel['history_proof']['new_dynamics']==0


@pytest.mark.parametrize('shift',[(0,0),(1,2),(15,15),(7,8)])
def test_shift_direction(shift):
    field=np.arange(256,dtype=float).reshape(16,16)/256
    p=system.old.encode(field);a=system.shift_packet(p,np.array(shift,np.int64));b=audit.shifted(p,shift)
    assert a==b
    actual=system.old.decode(a)
    for y in range(16):
        for x in range(16):assert actual[y,x]==field[(y+shift[0])%16,(x+shift[1])%16]
    np.testing.assert_array_equal(np.sort(actual.ravel()),np.sort(field.ravel()))


def test_reuse_accounting(panel):
    entries=[e for n in panel['meta']['cells'] for case in n for e in case]
    assert len(entries)==192 and sum(e['source_mode']=='natural_diagonal' for e in entries)==96
    assert sum(e['new_assay'] for e in entries)==panel['meta']['new_assays']
    assert all(not e['new_assay'] for e in entries if e['kind'] in ('copy','write_off'))
    assert len(system.CASES)*3*2*4*16==12288 and run.contract()['max_new_assays']==3072


def test_matching(panel):
    raw=panel['raw']
    for ci in range(32):np.testing.assert_array_equal(raw['terminal_states'][:,ci,:,0],raw['terminal_states'][:,0,:,0])
    assert not np.array_equal(raw['terminal_states'][0,0,0,0],raw['terminal_states'][1,0,0,0])
    for g in (1,2):assert not np.array_equal(raw['terminal_states'][0,0,g,0],raw['terminal_states'][0,0,g-1,0])
    assert system.PHYSICS_TAG==system.source.PHYSICS_TAG!=system.TAG


def test_independent_replay(panel,monkeypatch):
    for name in ('simulate_life','readout','shift_packet','cell'):monkeypatch.setattr(system,name,forbidden)
    for name in ('read_selected','write_streams','route','record'):monkeypatch.setattr(system.old,name,forbidden)
    assert checked(panel,True)['replayed_new_assays']==panel['meta']['new_assays']


def test_saved_no_dynamics(panel,monkeypatch):
    monkeypatch.setattr(audit.physics,'step',forbidden)
    assert checked(panel)['replayed_new_assays']==0
    assert history_check.check_life(panel['rows'],system.DISPOSABLE,0,panel['source'],panel['source_meta'],
        panel['upstream'],panel['upstream_meta'])['new_dynamics']==0


@pytest.mark.parametrize('key',['packet','terminal_packet','shift','terminal_states','terminal_values','record_values','guide','founder_packets'])
def test_corruption(panel,key):
    raw=panel['raw'].copy();raw[key]=raw[key].copy()
    if raw[key].dtype==np.uint8:raw[key].flat[0]^=1
    else:raw[key].flat[0]+=1
    with pytest.raises((AssertionError,ValueError)):checked(panel,raw=raw)


@pytest.mark.parametrize('key,value',[('tag','old'),('physics_namespace',system.TAG),('source_run','wrong'),
    ('source_state_given_to_reader',True),('assay_enters_lineage',True),('new_founders',1),('new_independent_noise',True),
    ('guide_refitted',True),('placement_supplied_by_analyst',False)])
def test_metadata_corruption(panel,key,value):
    meta=copy.deepcopy(panel['meta']);meta[key]=value
    with pytest.raises((AssertionError,ValueError)):checked(panel,meta=meta)


@pytest.mark.parametrize('key,value',[('packet_stop',999),('address_stop',999),('forward_shift',[4,5]),
    ('new_assay',True),('source_mode','new_assay'),('packet_sha256','fake'),('donor_case',99),('assay_steps',600)])
def test_cell_metadata_corruption(panel,key,value):
    meta=copy.deepcopy(panel['meta']);meta['cells'][0][0][0][key]=value
    with pytest.raises((AssertionError,ValueError)):checked(panel,meta=meta)


def test_condition_order(panel):
    raw,meta=system.simulate_life(system.DISPOSABLE,0,panel['source'],panel['source_meta'],tuple(reversed(system.CASES)))
    for k,v in raw.items():np.testing.assert_array_equal(v,panel['raw'][k])
    assert meta=={k:v for k,v in panel['meta'].items() if k!='replay'}
    with pytest.raises(ValueError):system.simulate_life(system.DISPOSABLE,0,panel['source'],panel['source_meta'],system.CASES[:-1])


@pytest.mark.parametrize('index,life',[(93016,0),(92000,0),(True,0),(93000,4),(93000,False)])
def test_namespace_guard(index,life):
    with pytest.raises(ValueError):system.source.source.validate(index,life)
    with pytest.raises(ValueError):system.shift_packet(bytes(2048),np.array([16,0],np.int64))
    with pytest.raises(ValueError):system.shift_packet(bytes(2048),np.array([1.,0.]))


def test_existing_endpoints(panel):
    for n in (0,1):
        for ci,case in enumerate(panel['meta']['cells'][n]):
            for gi,e in enumerate(case):
                if not e['new_assay']:
                    pi=e['recipient_case']
                    np.testing.assert_array_equal(panel['raw']['terminal_states'][n,ci,gi],panel['source']['terminal_states'][n,pi,gi])
                    np.testing.assert_array_equal(panel['raw']['terminal_packet'][n,ci,gi],panel['source']['terminal_packet'][n,pi,gi])


def test_independent_plan(panel,monkeypatch):
    a=system.block_plan(system.DISPOSABLE,panel['source_block'],panel['block_meta'])
    monkeypatch.setattr(system,'cell',forbidden);monkeypatch.setattr(system,'readout',forbidden)
    b=audit.block_plan(system.DISPOSABLE,panel['source_block'],panel['block_meta'])
    assert a==b and a['new_assays']<=192 and a['labelled_cells']==768


def test_same_label_not_alias(panel):
    entries=[e for n in panel['meta']['cells'] for case in n for e in case]
    assert any(e['new_assay'] and e['natural_selector']['inferred_family']==e['address_selector']['inferred_family'] for e in entries)
    assert all(not e['new_assay'] for e in entries if e['routed_sha256']==e['natural_routed_sha256'])


def test_tied_identity():
    p=bytes(2048);r,_,selection=system.old.route(p,'learned',system.old.load_guide())
    assert r==p and selection['family_tie'] and selection['chosen_forward_shift']==[0,0]
    assert system.shift_packet(p,np.array([0,0],np.int64))==audit.shifted(p,(0,0))==p


def test_constant_assay(panel):
    assert panel['raw']['terminal_states'].shape==(2,32,3,4,3,16,16)
    assert tuple(system.CONFIG.times)==(0,1,100,300)
    assert all(e['assay_steps']==300 for n in panel['meta']['cells'] for case in n for e in case)


def test_same_history_not_new_lineage(panel,monkeypatch):
    monkeypatch.setattr(system.old,'write_streams',forbidden)
    monkeypatch.setattr(system.source.source,'generate_founders',forbidden)
    raw,_=system.simulate_life(system.DISPOSABLE,0,panel['source'],panel['source_meta'])
    for k,v in raw.items():np.testing.assert_array_equal(v,panel['raw'][k])
    assert run.contract()['new_upstream_dynamics']==0 and run.contract()['fresh_cohort'] is False


def test_assay_isolation(panel,monkeypatch):
    original=system.readout
    def altered(*a,**k):
        states,meta=original(*a,**k);return states+.007,meta
    monkeypatch.setattr(system,'readout',altered)
    raw,_=system.simulate_life(system.DISPOSABLE,0,panel['source'],panel['source_meta'])
    for k in ('packet','terminal_packet','shift','record_values','guide','founder_packets'):
        np.testing.assert_array_equal(raw[k],panel['raw'][k])
    for n in (0,1):
        for ci,case in enumerate(panel['meta']['cells'][n]):
            for gi,e in enumerate(case):
                assert np.array_equal(raw['terminal_states'][n,ci,gi],panel['raw']['terminal_states'][n,ci,gi])==(not e['new_assay'])


def test_new_assay_replay_corruption(panel):
    n,ci,gi=next((n,ci,g) for n in (0,1) for ci,c in enumerate(panel['meta']['cells'][n]) for g,e in enumerate(c) if e['new_assay'])
    raw=panel['raw'].copy();raw['terminal_states']=raw['terminal_states'].copy();raw['terminal_values']=raw['terminal_values'].copy()
    raw['terminal_states'][n,ci,gi,-1,2,0,0]+=.007
    raw['terminal_values'][n,ci,gi]=system.source.source.observations(raw['terminal_states'][n,ci,gi],system.CASES[ci][0])
    assert checked(panel,raw=raw)['replayed_new_assays']==0
    with pytest.raises(AssertionError):checked(panel,True,raw=raw)


def test_no_source_mutation(panel):
    paths=(*system.source_paths(system.DISPOSABLE),*system.source.source_paths(system.DISPOSABLE))
    assert run.io.hashes(paths)==panel['source_hashes']
    assert all(not v.flags.writeable for v in panel['source'].values())
    assert all(not v.flags.writeable for v in panel['upstream'].values())
    for p in (1000,1300):
        for role in (0,1):
            for k in system.KINDS:
                a=system.CASES.index((role,p,1000,k));b=system.CASES.index((role,p,1300,k))
                np.testing.assert_array_equal(panel['raw']['packet'][:,a],panel['raw']['packet'][:,b])
                np.testing.assert_array_equal(panel['raw']['record_values'][:,a,:,:4],panel['raw']['record_values'][:,b,:,:4])


def test_external_roundtrip(panel):
    for k,v in run.io.load_npz(panel['directory']/'raw.npz').items():np.testing.assert_array_equal(v,panel['raw'][k])
    with pytest.raises(FileExistsError):run.io.write_npz(panel['directory']/'raw.npz',panel['raw'],run.ROOT)


def test_schema_roundtrip(panel):
    meta=run.io.read_json(panel['directory']/'meta.json');raw=run.io.load_npz(panel['directory']/'raw.npz')
    assert isinstance(meta['host']['tissue']['strict_band'],list)
    assert checked(panel,raw=raw,meta=meta)['labelled_cells']==192


def test_history_independent(panel,monkeypatch):
    for name in ('extract_life','profiles','features'):monkeypatch.setattr(history,name,forbidden)
    for name in ('read_selected','write_streams','route','record'):monkeypatch.setattr(system.old,name,forbidden)
    assert history_check.check_life(panel['rows'],system.DISPOSABLE,0,panel['source'],panel['source_meta'],
        panel['upstream'],panel['upstream_meta'])['passes']


@pytest.mark.parametrize('where',['incoming','read','write','stops','first','final_negative'])
def test_history_corruption(panel,where):
    rows=copy.deepcopy(panel['rows']);row=rows[0];stage=row['stages'][0]
    if where=='incoming':stage['incoming']['own_shape']+=.1
    elif where in ('read','write'):stage[where][0]['reference_own_shape']+=.1
    elif where=='stops':stage['stops'][0]['preference']+=.1
    elif where=='first':row['first_negative_assay_stage']='G9_999'
    else:row['final_negative']=not row['final_negative']
    with pytest.raises(AssertionError):history_check.check_life(rows,system.DISPOSABLE,0,panel['source'],
        panel['source_meta'],panel['upstream'],panel['upstream_meta'])


def test_history_counts(panel,monkeypatch):
    rows=copy.deepcopy(panel['rows']*64);s=history.summarize(rows)
    monkeypatch.setattr(history,'summarize',forbidden)
    assert history_check.check_summary(s,rows)['passes']
    assert s['history_rows']==256 and not s['early_branches_propagated'] and not s['predictive_validation']
    for group in s['groups']:
        for counts in group['first'].values():assert sum(counts.values())==128
        assert all(sum(t['counts'].values())==128 for t in group['transitions'])
    s['groups'][0]['cases']=64
    with pytest.raises(AssertionError):history_check.check_summary(s,rows)


def test_sixteen_block_normalization():
    x=np.broadcast_to(np.arange(16,dtype=float)[:,None,None],(16,4,2));draws=np.tile(np.arange(16),(10000,1))
    a=analysis.stats(x,draws);assert a['mean']==7.5 and a['pointwise_block_bootstrap_95']==[7.5,7.5]
    audit.physics.nested(a,independent.stats(x,draws))
    with pytest.raises(ValueError):analysis.stats(x[:8],draws)


def test_block_bootstrap():
    x=np.arange(128,dtype=float).reshape(16,4,2)/128;draws=np.zeros((10000,16),int)
    s=analysis.stats(x,draws);assert s['pointwise_block_bootstrap_95']==[x[0].sum()/8]*2
    audit.physics.nested(s,independent.stats(x,draws))


def test_decomposition():
    x=analysis.decompose(.125,.25,.375,.75);y=independent.pieces(.125,.25,.375,.75)
    assert x==y and x['natural_change']==.625 and x['earlier_placement_on_late']==-.375
    assert x['content_symmetric']+x['placement_symmetric']==x['natural_change']


def test_interaction():
    pure=analysis.decompose(0.,.125,.25,.375);assert pure['interaction']==0.
    interacted=analysis.decompose(0.,.125,.25,.5);assert interacted['interaction']==.125
    assert interacted==independent.pieces(0.,.125,.25,.5)


def synthetic(effect=0.):
    blocks=[];records=[]
    for _ in range(16):
        b=dict(terminal_values=np.zeros((4,2,32,3,4,2)),record_values=np.zeros((4,2,32,3,7)))
        cells=[]
        for ci,(r,p,a,k) in enumerate(system.CASES):
            v=.25 if k in ('intact','copy') else 0.
            if (r,p,a,k)==(1,1300,1000,'intact'):v+=effect
            b['terminal_values'][:,:,ci,:,-1,0]=v;b['record_values'][:,:,ci,:,0]=.8 if a==1000 else .4
            mode='natural_diagonal' if p==a else 'identical_routed_bytes'
            cells.append([dict(natural_selector=dict(inferred_family=r),address_selector=dict(inferred_family=r),
                source_mode=mode,new_assay=False) for g in (1,2,3)])
        blocks.append(b);records.append(dict(lives=[dict(cells=[copy.deepcopy(cells),copy.deepcopy(cells)]) for l in range(4)]))
    return blocks,records


def test_complete_summary(monkeypatch):
    b,m=synthetic(.125);s=analysis.summarize(b,m)
    monkeypatch.setattr(analysis,'summarize',forbidden);monkeypatch.setattr(analysis,'decompose',forbidden)
    assert independent.check(s,b,m)['passes'] and s['primary']['mean']==.125
    assert s['label']=='B_G2_EARLIER_PLACEMENT_FAVORED'
    assert [len(s[k]) for k in ('groups','decompositions','controls','copy_contrasts')]==[96,24,72,24]
    s['primary']['mean']+=.01
    with pytest.raises(AssertionError):independent.check(s,b,m)


def test_primary_not_shape():
    b,m=synthetic(-.0625);s=analysis.summarize(b,m)
    assert s['primary']['mean']==-.0625 and s['label']=='B_G2_LATER_PLACEMENT_FAVORED'
    assert independent.check(s,b,m)['passes']


def test_primary_g2_not_g3():
    b,m=synthetic(.125);ci=system.CASES.index((1,1300,1000,'intact'))
    for block in b:block['terminal_values'][:,:,ci,2,-1,0]=.25-.0625
    s=analysis.summarize(b,m)
    assert s['primary']['mean']==.125 and s['label']=='B_G2_EARLIER_PLACEMENT_FAVORED'
    assert independent.check(s,b,m)['passes']


def test_control_gate_not_primary():
    b,m=synthetic(.125);ci=system.CASES.index((0,1000,1000,'read_off'))
    for block in b:block['terminal_values'][:,:,ci,0,-1,0]=.9
    s=analysis.summarize(b,m)
    assert s['label']=='APPARATUS_NOT_QUALIFIED' and s['primary_interval_classification']=='B_G2_EARLIER_PLACEMENT_FAVORED'
    assert s['primary']['mean']==.125 and independent.check(s,b,m)['passes']


def test_constant_unresolved():
    b,m=synthetic();s=analysis.summarize(b,m)
    assert s['label']=='B_G2_PLACEMENT_DIFFERENCE_UNRESOLVED' and s['primary']['pointwise_block_bootstrap_95']==[0.,0.]
    assert not s['equivalence_test'] and independent.check(s,b,m)['passes']


def test_source_closure():
    files=run.source_closure();assert len(files)>=1640
    assert all(system.dev.WS/p in files for p in run.SCIENCE)
    assert system.dev.WS/'stopping-time/RESULTS.md' in files
    assert system.dev.WS/'packet-placement/README.md' not in files


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
    rd,wr=os.pipe();monkeypatch.setenv('D148_READY_FD',str(wr));run.signal_ready('execute')
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
    code="""from l20_extension1 import placement_run as r
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
