"""Synthetic D167 qualification, independent algebra and forbidden-access guards."""
import ast
from copy import deepcopy
import inspect
import time
import numpy as np
import pytest
from l20_extension1 import passive_stages as m, passive_stages_check as c, passive_stages_run as run


def forbid(*args,**kwargs):raise AssertionError('forbidden fit, dynamics or outcome access')


def encode(field):return np.frombuffer(np.asarray(field,dtype='<f8').tobytes(),dtype=np.uint8).copy()


def route(field,guide):
    g=guide-guide.mean(axis=(1,2),keepdims=True);g/=g.std(axis=(1,2),keepdims=True)
    centered=field-field.mean();scale=centered.std()
    scores=np.array([np.sum(centered*np.roll(t,(i,j),(0,1)))/(256*scale) if scale else 0.
        for t in g for i in range(16) for j in range(16)]).reshape(2,16,16)
    maxima=scores.max(axis=(1,2));family=int(np.argmax(maxima))
    shift=(0,0) if abs(maxima[0]-maxima[1])<=1e-12 else tuple(np.argwhere(abs(scores[family]-maxima[family])<=1e-12)[0])
    return np.roll(field,tuple(-v for v in shift),(0,1)),scores


def fixture(seed=42):
    rng=np.random.default_rng(seed)
    raw={k:np.zeros(shape,dtype=np.uint8 if k in m.PACKETS else np.int64 if k=='shift' else np.float64)
        for k,shape in m.SHAPES.items()}
    guide=c.templates()+.04*rng.normal(size=(2,16,16));raw['guide'][:]=guide
    for key in ('read_states','write_states','terminal_states'):
        raw[key][:]=rng.normal(size=raw[key].shape)*.4
    for key in ('read_states','terminal_states'):
        for k in (1,2):raw[key][:,:,:,0,k]=raw[key][:,:,:,0,0]
    raw['read_states'][:,1]=raw['read_states'][:,0];raw['read_states'][:,3]=raw['read_states'][:,2]
    raw['write_states'][:,:,:,0,:3]=raw['read_states'][:,:,:,-1]
    raw['write_states'][:,:,:,0,3]=0
    raw['write_states'][:,1,:,:2]=raw['write_states'][:,0,:,:2]
    raw['write_states'][:,3,:,:2]=raw['write_states'][:,2,:,:2]
    for life in range(4):
        for role in range(2):
            field=.3*c.templates()[role]+.1*rng.normal(size=(16,16));field-=field.mean()
            raw['founder_packets'][life,role]=encode(field)
        for group in range(4):
            for copy in range(2):
                raw['input'][life,group,copy]=raw['founder_packets'][life,group//2]
                ref=raw['write_states'][life,group,copy,-1,2]
                ref+=.6*c.templates()[group//2]
                out=np.tanh(ref);out-=out.mean();out*=.3/out.std()
                raw['outgoing'][life,group,copy]=encode(out)
                for phase,(before,after) in enumerate((('input','routed'),('outgoing','terminal_packet'))):
                    field=c.packet(raw[before][life,group,copy]);routed,scores=route(field,guide)
                    raw[after][life,group,copy]=encode(routed);raw['scores'][life,group,copy,phase]=scores
    measured=m.extract(raw);start,end=m.endpoints(measured)
    raw['initial_features'][:]=start[:,:,0];raw['diagnostic_features'][:]=end
    return raw,measured


@pytest.fixture(scope='module')
def one():return fixture()


@pytest.fixture(scope='module')
def panel(one):
    _,x=one;di=np.arange(4,dtype=np.int64);pi=np.arange(20,26,dtype=np.int64)
    a={co+'_'+k:np.stack([v+i*.001 for i in range(len(ids))])
        for co,ids in (('development',di),('pilot',pi)) for k,v in x.items()}
    return a,di,pi,m.summarize(a,di,pi)


def test_one_block(one):
    raw,got=one;p=c.block(raw,got)
    assert p['passes'] and p['fields']==1536 and p['max_measurement_error']<2e-10


def test_full_panel_roundtrip(tmp_path,record_property,monkeypatch,one):
    assert run.ROOT in tmp_path.parents
    for name in ('solve','svd','lstsq'):monkeypatch.setattr(np.linalg,name,forbid)
    start=time.monotonic();base,_=one;a={};proofs=[]
    di=np.arange(90000,90016,dtype=np.int64);pi=np.arange(100000,100064,dtype=np.int64)
    for co,ids in (('development',di),('pilot',pi)):
        rows=[]
        for j in range(len(ids)):
            # Complete blocks, rotating lives; fixture is algebra, not physics.
            raw={k:np.roll(v,j%4,axis=0) for k,v in base.items()}
            got=m.extract(raw);proofs.append(c.block(raw,got));rows.append(got)
        for k in ('fields','preference'):a[co+'_'+k]=np.stack([r[k] for r in rows])
    s=m.summarize(a,di,pi);proof=c.summary(s,a,di,pi)
    run.io.write_npz(tmp_path/'stages.npz',a,run.ROOT);run.io.write_json(tmp_path/'summary.json',s,run.ROOT)
    saved=run.io.load_npz(tmp_path/'stages.npz');c.same(saved,a)
    assert c.summary(run.io.read_json(tmp_path/'summary.json'),saved,di,pi)==proof
    assert sum(p.stat().st_size for p in tmp_path.iterdir())<run.source.ALLOWANCE
    assert sum(p['fields'] for p in proofs)==122880
    with pytest.raises(FileExistsError):run.io.write_npz(tmp_path/'stages.npz',a,run.ROOT)
    record_property('full_panel_seconds',time.monotonic()-start);record_property('founders',80)
    record_property('fields',122880);record_property('summary_rows',1236)


def test_no_dynamics_or_fit(one,monkeypatch):
    for module in (m,c,run):
        for node in ast.walk(ast.parse(inspect.getsource(module))):
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute):
                assert node.func.attr not in ('fit','train','solve','svd','lstsq','predict','simulate','rollout',
                    'blueprint_step','read_trace','write_trace','read_selected','write_streams','simulate_life')
    for name in ('solve','svd','lstsq'):monkeypatch.setattr(np.linalg,name,forbid)
    assert c.block(*one)['passes']


@pytest.mark.parametrize('co',['development','pilot'])
def test_loader_excludes_outcomes(monkeypatch,co):
    seen=[];n=len(run.IDS[co])
    class Archive:
        files=['start','endpoint','targeted']+(['labels','futures','block_ids'] if co=='development' else [])
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def __getitem__(self,key):
            seen.append(key)
            if key=='block_ids':return np.asarray(run.IDS[co],dtype=np.int64)
            if key=='start':return np.ones((n,4,4,7))
            if key=='endpoint':return np.ones((n,4,4,3,6))
            forbid()
    monkeypatch.setattr(run.np,'load',lambda *a,**kw:Archive())
    start,end=run.feature_members('synthetic',co)
    assert set(seen)=={'start','endpoint'}|({'block_ids'} if co=='development' else set())
    assert start.shape[-1]==4 and end.shape[-2:]==(2,6)


def test_raw_loader_slices_challenge(monkeypatch,one):
    raw,_=one;seen=[]
    class Archive:
        files=list(m.SHAPES)+list(run.EXTRA)
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def __getitem__(self,key):
            seen.append(key);assert key in raw
            x=raw[key]
            if key in ('guide','founder_packets','initial_features'):return x.copy()
            return np.concatenate((x,np.zeros_like(x[:,:,:1])),axis=2)
    monkeypatch.setattr(run.np,'load',lambda *a,**kw:Archive())
    result=run.load_raw('synthetic');c.same(result,raw)
    assert set(seen)==set(raw) and all(not x.flags.writeable for x in result.values())


@pytest.mark.parametrize('key',['input','routed','outgoing','terminal_packet','read_states','write_states',
    'scores','guide','initial_features','diagnostic_features'])
def test_corruption(one,key):
    raw,got=deepcopy(one)
    if raw[key].dtype==np.uint8:raw[key].flat[7]^=128
    else:raw[key].flat[-1]+=.1
    with pytest.raises((AssertionError,ValueError)):c.block(raw,got)


@pytest.mark.parametrize('key',['fields','preference'])
def test_output_corruption(one,key):
    raw,got=deepcopy(one);got[key].flat[101]+=.1
    with pytest.raises(AssertionError):c.block(raw,got)


@pytest.mark.parametrize('key',['labels','futures','outcomes'])
def test_extra_outcome_rejected(one,key):
    raw,_=deepcopy(one);raw[key]=np.ones(1)
    with pytest.raises(AssertionError):m.extract(raw)


def test_constant_fields():
    x=np.ones((4,4,2,48,16,16))*2;guide=np.tile(c.templates(),(4,1,1,1))
    got=m.measurements(x,guide);want,_=c.direct(x,guide);c.same(got,want)
    np.testing.assert_array_equal(got[...,:4],0);np.testing.assert_array_equal(got[...,4],2)


def test_known_translation():
    x=np.empty((4,4,2,48,16,16));guide=np.tile(c.templates(),(4,1,1,1))
    for g in range(4):x[:,g]=np.roll(c.templates()[g//2],(3,5),(0,1))
    a=m.measurements(x,guide);b,_=c.direct(x,guide);c.same(a,b)
    np.testing.assert_allclose(a[...,0],1,atol=1e-12);np.testing.assert_allclose(a[...,1],0,atol=1e-12)
    np.testing.assert_allclose(a[...,2],1,atol=1e-12)
    assert not np.allclose(a[...,3],1)


def test_preference_strict_boundary(one):
    raw,_=deepcopy(one)
    for g in range(4):raw['terminal_states'][:,g,:,:,0]=.2*c.templates()[g//2]
    np.testing.assert_array_equal(m.preference(raw),0);np.testing.assert_array_equal(c.preferences(raw),0)
    raw['terminal_states'][...,0,:,:]*=1.0001
    np.testing.assert_array_equal(m.preference(raw),.5);np.testing.assert_array_equal(c.preferences(raw),.5)


def test_copy_reversal(panel):
    a,di,pi,s=panel;b={k:np.flip(v,axis=3).copy() for k,v in a.items()};other=m.summarize(b,di,pi)
    c.summary(other,b,di,pi)
    for old,new in zip(s['field_rows'],other['field_rows']):
        for co in ('development','pilot'):
            c.same(new[co]['gap_mean'],-old[co]['gap_mean'])
            c.same(new[co]['founder_gap'],[-v for v in old[co]['founder_gap']])


def test_founder_permutation(panel):
    a,di,pi,s=panel;b={k:v[::-1].copy() for k,v in a.items()};other=m.summarize(b,di[::-1],pi[::-1])
    c.summary(other,b,di[::-1],pi[::-1])
    for old,new in zip(s['field_rows'],other['field_rows']):
        for co in ('development','pilot'):
            c.same(new[co]['gap_mean'],old[co]['gap_mean'])
            c.same(new[co]['founder_gap'],old[co]['founder_gap'][::-1])


def test_concentration():
    x=np.zeros((4,4,2));x[2,:,1]=.8;ids=np.arange(4,dtype=np.int64)
    got=m.describe(x,ids);c.same(got,c.describe(x,ids))
    assert got['largest_absolute_founder']==2 and got['largest_absolute_share']==1
    assert got['gap_mean']==.2 and got['omission_minimum']==0


def test_zero_concentration():
    x=np.ones((4,4,2));ids=np.arange(4,dtype=np.int64);got=m.describe(x,ids)
    c.same(got,c.describe(x,ids));assert got['largest_absolute_share'] is None and got['numerical_zero']==4


def test_sign_tolerance():
    x=np.zeros((4,4,2));x[:,:,1]=np.array([.5e-12,-.5e-12,2e-12,-2e-12])[:,None]
    d=m.describe(x,np.arange(4,dtype=np.int64));assert (d['positive'],d['negative'],d['numerical_zero'])==(1,1,2)


def test_reference_telescopes(panel):
    _,_,_,s=panel
    for g in m.GROUPS:
        for metric in m.METRICS:
            edges=[r for r in s['transition_rows'] if r['group']==g and r['metric']==metric]
            rows={r['stage']:r for r in s['field_rows'] if r['group']==g and r['metric']==metric}
            for co in ('development','pilot'):
                c.same(sum(r[co]['gap_mean'] for r in edges),rows[m.CHAIN[-1]][co]['gap_mean']-rows[m.CHAIN[0]][co]['gap_mean'])


@pytest.mark.parametrize('kind',['scalar','founder','transition'])
def test_summary_corruption(panel,kind):
    a,di,pi,s=deepcopy(panel)
    if kind=='scalar':s['field_rows'][5]['pilot']['gap_mean']+=.1
    elif kind=='founder':s['field_rows'][5]['development']['founder_gap'][1]+=.1
    else:s['transition_rows'][10]['pilot']['omission_maximum']+=.1
    with pytest.raises(AssertionError):c.summary(s,a,di,pi)


@pytest.mark.parametrize('stage',['execute','audit'])
def test_stage_guard(monkeypatch,stage):
    monkeypatch.delenv(run.ENV,raising=False)
    run.stage_guard({'must_detach':False},stage)
    with pytest.raises(AssertionError):run.stage_guard({'must_detach':True},stage)
    monkeypatch.setenv(run.ENV,stage);monkeypatch.setattr(run.os,'getsid',lambda n:12);monkeypatch.setattr(run.os,'getpid',lambda:13)
    with pytest.raises(AssertionError):run.stage_guard({'must_detach':True},stage)
    monkeypatch.setattr(run.os,'getpid',lambda:12);monkeypatch.setattr(run.sys.stdin,'isatty',lambda:False)
    run.stage_guard({'must_detach':True},stage)


def test_raw_path_scope():
    for co,index in [('development',90016),('pilot',100064),('pilot',90000),('wrong',100000)]:
        with pytest.raises(AssertionError):run.raw_paths(co,index)


def test_external_write_once(tmp_path):
    assert run.ROOT in tmp_path.parents
    p=tmp_path/'once.json';run.io.write_json(p,{'ok':True},run.ROOT)
    with pytest.raises(FileExistsError):run.io.write_json(p,{'ok':False},run.ROOT)
    with pytest.raises(ValueError):run.io.write_json(run.WS/'forbidden_d167_output.json',{},run.ROOT)


def test_hash_drift(tmp_path):
    p=tmp_path/'pin.json';run.io.write_json(p,{'ok':True},run.ROOT);seen={}
    with pytest.raises(AssertionError):run.source.bind(p,'0'*64,seen)
    assert not seen
