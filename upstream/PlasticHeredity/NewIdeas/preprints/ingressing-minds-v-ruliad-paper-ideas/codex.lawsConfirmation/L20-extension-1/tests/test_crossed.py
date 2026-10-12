"""D143: synthetic statistics and already-observed disposable dynamics only."""
import copy
import inspect
import json
import os
from pathlib import Path
import numpy as np
import pytest
from l20_extension1 import crossed_system as system, crossed_audit as audit
from l20_extension1 import crossed_analysis as analysis, crossed_analysis_check as independent
from l20_extension1 import crossed_run as run, predictor


def forbidden(*args, **kwargs):
    raise AssertionError('forbidden production/dynamic/fit access')


@pytest.fixture(scope='module')
def cell(tmp_path_factory):
    founders, guides = system.load_source(system.DISPOSABLE)
    raw, meta = system.simulate(system.DISPOSABLE, 0, 0, 1, founders[0], guides[0])
    meta['replay'] = audit.check(raw, meta, founders[0], guides[0], True)
    directory = tmp_path_factory.mktemp('crossed_disposable_cell')
    run.io.write_npz(directory/'raw.npz', raw, run.ROOT)
    run.io.write_json(directory/'meta.json', meta, run.ROOT)
    return dict(raw=raw, meta=meta, founders=founders[0], guide=guides[0], directory=directory)


def test_full_disposable_cell(cell):
    assert cell['meta']['replay']['full_dynamics_replayed']
    assert cell['meta']['replay']['generation_paths'] == 12
    assert cell['meta']['replay']['terminal_paths'] == 4
    assert cell['meta']['replay']['new_founders'] == 0


def test_all_diagonal_bridges(cell):
    saved, records = system.load_diagonal(system.DISPOSABLE)
    for noise in range(4):
        raw, meta = system.simulate(system.DISPOSABLE, 0, noise, noise, cell['founders'], cell['guide'])
        meta['replay'] = audit.check(raw, meta, cell['founders'], cell['guide'], True)
        assert audit.diagonal(raw, meta, {k:v[0,noise] for k,v in saved.items()}, records['lives'][0][noise])


def test_rng_factorization():
    for noise in range(4):
        for address in range(4):
            for phase in system.PHASES:
                level = address if phase.endswith(':source_shift') else noise
                a = system.rng(90000,0,noise,address,phase).standard_normal(16)
                b = system.source.rng(90000,0,level,phase).standard_normal(16)
                np.testing.assert_array_equal(a,b)
    assert not np.array_equal(system.rng(90000,0,0,1,'g1:read').standard_normal(16),
                              system.rng(90000,0,1,1,'g1:read').standard_normal(16))


def test_diagonal_metadata_json_roundtrip():
    raw, records = system.load_diagonal(system.DISPOSABLE)
    saved = records['lives'][0][0]
    meta = copy.deepcopy(saved)
    meta.update(noise_id=0, address_id=0, noise_namespace=saved['namespace'],
                address_namespace=saved['namespace'])
    meta['host']['tissue']['strict_band'] = tuple(meta['host']['tissue']['strict_band'])
    meta['host']['ladder']['displacement_ladder'] = tuple(meta['host']['ladder']['displacement_ladder'])
    arrays = {k:v[0,0] for k,v in raw.items()}
    assert audit.diagonal(arrays, meta, arrays, saved)
    meta['host']['tissue']['strict_band'] = (.006, .5)
    with pytest.raises(AssertionError): audit.diagonal(arrays, meta, arrays, saved)


def test_aligned_aliases(cell):
    other, meta = system.simulate(system.DISPOSABLE,0,0,2,cell['founders'],cell['guide'])
    audit.check(other,meta,cell['founders'],cell['guide'],True)
    for key in other:
        if key in ('founder_packets','guide','targets','shift'): continue
        for ci in (1,3): np.testing.assert_array_equal(other[key][ci],cell['raw'][key][ci])
    for ci in range(4):
        np.testing.assert_array_equal(other['read_states'][ci,0],cell['raw']['read_states'][ci,0])
        np.testing.assert_array_equal(other['write_states'][ci,0,:2],cell['raw']['write_states'][ci,0,:2])


def test_independent_replay(cell,monkeypatch):
    monkeypatch.setattr(system,'simulate',forbidden)
    for name in ('read_selected','write_streams','route','record'): monkeypatch.setattr(system.old,name,forbidden)
    assert audit.check(cell['raw'],cell['meta'],cell['founders'],cell['guide'],True)['full_dynamics_replayed']


def test_saved_no_dynamics(cell,monkeypatch):
    monkeypatch.setattr(audit.physics,'step',forbidden)
    assert not audit.check(cell['raw'],cell['meta'],cell['founders'],cell['guide'],False)['full_dynamics_replayed']


@pytest.mark.parametrize('key',['incoming','routed','outgoing','scores','read_states','write_states',
    'terminal_input','terminal_packet','terminal_scores','terminal_states','values','terminal_values','shift'])
def test_corruption(cell,key):
    raw = {k:v.copy() for k,v in cell['raw'].items()}
    if raw[key].dtype == np.uint8: raw[key].flat[0] ^= 1
    else: raw[key].flat[0] += 1
    with pytest.raises((AssertionError,ValueError)): audit.check(raw,cell['meta'],cell['founders'],cell['guide'],False)


@pytest.mark.parametrize('key,value',[('noise_id',1),('address_id',2),('noise_namespace','wrong'),
    ('address_namespace','wrong'),('old_lineage_states_reused',True),('parent_state_access',True),
    ('source_records_reused',False),('recombined_existing_streams',False),('guide_refitted',True),('record_bytes',64)])
def test_metadata_corruption(cell,key,value):
    meta=copy.deepcopy(cell['meta']); meta[key]=value
    with pytest.raises((AssertionError,ValueError)): audit.check(cell['raw'],meta,cell['founders'],cell['guide'],False)


def test_condition_order(cell):
    raw, meta=system.simulate(system.DISPOSABLE,0,0,1,cell['founders'],cell['guide'],tuple(reversed(system.CASES)))
    for key in raw: np.testing.assert_array_equal(raw[key],cell['raw'][key])
    assert meta=={k:v for k,v in cell['meta'].items() if k!='replay'}


def test_fresh_start_independent_of_order(cell):
    assert not cell['meta']['old_lineage_states_reused']
    for role in range(2):
        for ci in (2*role,2*role+1):
            np.testing.assert_array_equal(cell['raw']['incoming'][ci,0],cell['founders'][role])
    original=cell['founders'].copy()
    with pytest.raises(ValueError): system.simulate(system.DISPOSABLE,0,0,1,cell['founders'],cell['guide'],((0,'aligned'),))
    np.testing.assert_array_equal(cell['founders'],original)


@pytest.mark.parametrize('index,life,noise,address',[(78000,0,0,0),(90016,0,0,0),(90000,4,0,0),
    (90000,0,4,0),(90000,0,0,4),(True,0,0,0),(90000,0,False,0),(90000,0,0,True)])
def test_namespace_guard(index,life,noise,address):
    with pytest.raises(ValueError): system.rng(index,life,noise,address,'g1:birth')


def test_phase_guard():
    with pytest.raises(ValueError): system.rng(90000,0,0,0,'unregistered_phase')


def test_pure_noise():
    y=np.arange(64)[:,None,None]/100+np.tile(np.array([-.3,-.1,.1,.3])[:,None],(1,4))
    p=analysis.components(y)
    assert p['noise_main']==pytest.approx(.2/3)
    assert p['address_main']==pytest.approx(0,abs=1e-15)
    assert p['interaction']==pytest.approx(0,abs=1e-15)
    assert p['address_at_fixed_noise']==pytest.approx(0,abs=1e-15)


def test_pure_address():
    y=np.broadcast_to(np.array([-.3,-.1,.1,.3]),(64,4,4))
    p=analysis.components(y)
    assert p['address_main']==pytest.approx(.2/3)
    assert p['noise_main']==pytest.approx(0,abs=1e-15)
    assert p['noise_at_fixed_address']==pytest.approx(0,abs=1e-15)


def test_interaction_negative_components():
    y=np.tile(np.outer([-1,1,-1,1],[-1,1,-1,1]),(64,1,1))
    p=analysis.components(y)
    assert p['noise_main']==pytest.approx(-4/9) and p['address_main']==pytest.approx(-4/9)
    assert p['interaction']==pytest.approx(16/9)
    assert p['finite_total']==pytest.approx(1)
    assert p['noise_at_fixed_address']==pytest.approx(4/3)
    assert p['address_at_fixed_noise']==pytest.approx(4/3)


def test_mixed_moments():
    y=np.random.default_rng(143).normal(size=(64,4,4))
    p,q=analysis.components(y),independent.moments(y)
    for k in p: np.testing.assert_allclose(p[k],q[k],atol=1e-12,rtol=0)
    transposed=analysis.components(y.swapaxes(-1,-2))
    assert p['noise_main']==pytest.approx(transposed['address_main'])
    assert p['interaction']==pytest.approx(transposed['interaction'])
    assert p['total']==pytest.approx(transposed['total'])


def test_constant_outcomes():
    p=analysis.group_statistics(np.full((16,4,4,4),.125),np.zeros((10000,16),int))
    for v in p.values(): assert v==dict(estimate=0.,pointwise_block_bootstrap_95=[0.,0.])


def test_block_bootstrap():
    y=np.random.default_rng(55).normal(size=(16,4,4,4))
    p=analysis.group_statistics(y,np.zeros((10000,16),int))
    q=independent.moments(np.tile(y[0],(16,1,1)))
    for k in q: np.testing.assert_allclose(p[k]['pointwise_block_bootstrap_95'],[q[k],q[k]],atol=1e-12,rtol=0)
    with pytest.raises(ValueError): analysis.group_statistics(y,np.zeros((10000,64),int))


@pytest.fixture(scope='module')
def expanded_source():
    saved, old_meta=system.load_diagonal(system.DISPOSABLE)
    raw={k:np.repeat(v[:,:,None],4,axis=2) for k,v in saved.items()}
    entries=[]
    for life in range(4):
        noises=[]
        for noise in range(4):
            cells=[]
            for address in range(4):
                raw['shift'][life,noise,address]=saved['shift'][life,address]
                m=copy.deepcopy(old_meta['lives'][life][noise])
                m.pop('future'); m.pop('namespace'); m.pop('fresh_future_noise')
                m.update(noise_id=noise,address_id=address,noise_namespace=system.namespace(noise),
                         address_namespace=system.namespace(address),recombined_existing_streams=True)
                cells.append(m)
            noises.append(cells)
        entries.append(noises)
    meta=dict(index=system.DISPOSABLE,config=old_meta['config'],lives=entries)
    return raw,meta


def test_cross_panel_alias_rejection(expanded_source):
    raw,meta=expanded_source
    proof=audit.crossed_panel(raw,meta)
    assert proof['aligned_address_aliases']==96 and proof['labelled_terminal_cells']==256
    broken=raw.copy(); broken['terminal_states']=raw['terminal_states'].copy()
    broken['terminal_states'][0,0,1,1,-1,0,0,0] += .1
    with pytest.raises(AssertionError): audit.crossed_panel(broken,meta)


def test_cross_panel_shift_rejection(expanded_source):
    raw,meta=expanded_source
    broken=raw.copy(); broken['shift']=raw['shift'].copy(); broken['shift'][0,1,0,0,0,0] += 1
    with pytest.raises(AssertionError): audit.crossed_panel(broken,meta)


@pytest.fixture(scope='module')
def score_fixture(expanded_source):
    raw,meta=expanded_source; blocks=[]
    for bi in range(16):
        b=raw.copy(); b['terminal_values']=raw['terminal_values'].copy()
        for life in range(4):
            for n in range(4):
                for a in range(4):
                    for ci in range(4):
                        b['terminal_values'][life,n,a,ci,-1,0]=.01*bi+.02*life+.01*n+.02*ci-.2+((.013*a+.005*n*a) if ci%2==0 else 0)
                        b['terminal_values'][life,n,a,ci,-1,1]=0
        blocks.append(b)
    return blocks,[meta]*16


def test_complete_summary(score_fixture,monkeypatch):
    summary=analysis.summarize(*score_fixture)
    monkeypatch.setattr(analysis,'case_components',forbidden); monkeypatch.setattr(analysis,'summarize',forbidden)
    assert independent.check(summary,*score_fixture)['passes']
    summary['groups']['B_translated']['primary']['address_main']['estimate'] += .1
    with pytest.raises(AssertionError): independent.check(summary,*score_fixture)


def test_no_prediction_use(score_fixture,monkeypatch):
    for name in ('fit','select_and_fit','predict'): monkeypatch.setattr(predictor,name,forbidden)
    assert analysis.summarize(*score_fixture)['refitted_models']==0
    assert 'existing_labels' not in inspect.getsource(run)


def test_external_roundtrip(cell,tmp_path):
    run.io.write_npz(tmp_path/'raw.npz',cell['raw'],run.ROOT)
    run.io.write_json(tmp_path/'meta.json',cell['meta'],run.ROOT)
    raw=run.io.load_npz(tmp_path/'raw.npz'); meta=run.io.read_json(tmp_path/'meta.json')
    assert audit.check(raw,meta,cell['founders'],cell['guide'],False)['packet_lineage']
    with pytest.raises(FileExistsError): run.io.write_json(tmp_path/'meta.json',{},run.ROOT)
    with pytest.raises(ValueError): run.io.write_json(Path('/tmp/d143_forbidden.json'),{},run.ROOT)


def test_source_closure():
    closure=run.source_closure()
    assert len(closure)>1300
    assert all(path in closure for path in system.source_paths(system.DISPOSABLE))
    assert all(system.dev.WS/p in closure for p in run.SCIENCE)


def test_resource_guards(monkeypatch):
    assert len(run.preflight(False))<=6
    monkeypatch.setenv('OMP_NUM_THREADS','2')
    with pytest.raises(RuntimeError): run.preflight(False)


def test_detached_guard(monkeypatch):
    monkeypatch.delenv(run.DETACHED_ENV,raising=False)
    with pytest.raises(RuntimeError): run.detached_guard(True)
    run.detached_guard(False)
    monkeypatch.setenv(run.DETACHED_ENV,'1'); monkeypatch.setattr(os,'getsid',lambda _:os.getpid())
    monkeypatch.setattr(os,'readlink',lambda p:'/dev/null' if p.endswith('/0') else str(run.log_path()))
    run.detached_guard(True)


def test_long_stage_guard(tmp_path,monkeypatch):
    monkeypatch.setattr(run,'preflight',lambda:None)
    monkeypatch.setattr(run,'frozen',lambda:dict(test_proof=dict(benchmark_forecast=601)))
    monkeypatch.setattr(run,'benchmark_dir',lambda:tmp_path/'never_created')
    monkeypatch.delenv(run.DETACHED_ENV,raising=False)
    with pytest.raises(RuntimeError): run.benchmark()
    assert not (tmp_path/'never_created').exists()


def test_startup_handshake(monkeypatch):
    read,write=os.pipe(); monkeypatch.setenv('D143_READY_FD',str(write))
    run.signal_ready('execute')
    try: assert json.loads(os.read(read,4096))==dict(stage='execute',pid=os.getpid(),status='STARTED')
    finally: os.close(read)
    assert 'D143_READY_FD' not in os.environ


def test_no_automatic_successor():
    c=run.contract()
    assert not c['automatic_polling'] and not c['automatic_retry'] and not c['automatic_successor']
    assert 'detach(' not in inspect.getsource(run.execute)
    assert 'execute(' not in inspect.getsource(run.benchmark)
    assert 'child.poll' not in inspect.getsource(run.detach)
    assert 'select.select([ready_read], [], [], 55)' in inspect.getsource(run.detach)
    assert c['aligned_address_aliases']==1536 and c['novel_ordinary_off_diagonal_cells']==1536


def test_main_barrier(tmp_path,monkeypatch):
    monkeypatch.setattr(system,'simulate',forbidden)
    with pytest.raises(ValueError,match='barrier'): run.worker(tmp_path,90000)
    directory=tmp_path/'run'; directory.mkdir(); run.io.write_json(directory/'MANIFEST.json',{'fixture':True},run.ROOT)
    digest=run.sha256_file(directory/'MANIFEST.json')
    with pytest.raises(FileNotFoundError): run.barrier(directory,tmp_path,digest)
    run.io.write_json(tmp_path/'CROSSED_PANEL_STARTED.json',dict(manifest_sha256=digest,
        source_complete_sha256=system.SOURCE_COMPLETE_SHA,namespaces=[system.namespace(r) for r in range(4)]),run.ROOT)
    assert run.barrier(directory,tmp_path,digest)['manifest_sha256']==digest
    with pytest.raises(AssertionError): run.barrier(directory,tmp_path,'wrong hash')


def test_failure_receipt(tmp_path,monkeypatch):
    directory=tmp_path/'run'; directory.mkdir(); out=tmp_path/'out'; out.mkdir()
    monkeypatch.setattr(run,'paths',lambda:(directory,out)); monkeypatch.setattr(run,'preflight',lambda:None)
    monkeypatch.setattr(run,'prepared',lambda:(_ for _ in ()).throw(RuntimeError('qualification failure fixture')))
    with pytest.raises(RuntimeError): run.execute()
    assert (directory/'FAILED.json').exists() and run.io.read_json(directory/'STATUS.json')['status']=='FAILED'
    with pytest.raises(FileExistsError): run.execute()
