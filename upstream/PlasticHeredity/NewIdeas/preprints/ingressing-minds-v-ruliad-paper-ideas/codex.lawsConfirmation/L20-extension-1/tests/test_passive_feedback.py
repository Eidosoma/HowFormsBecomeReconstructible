"""D168 synthetic qualification, complete accounting and adversarial checks."""
import ast
from copy import deepcopy
import importlib.util
import inspect
import time
import numpy as np
import pytest
from l20_extension1 import passive_feedback as m, passive_feedback_check as c, passive_feedback_run as run


def forbid(*args,**kwargs):raise AssertionError('forbidden outcome, fit or dynamics access')


@pytest.fixture(scope='module')
def one():
    # Reuse the frozen D167 algebra fixture, not any real source cohort.
    spec=importlib.util.spec_from_file_location('d167_fixture',run.WS/'tests/test_passive_stages.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    raw,saved=module.fixture(1854)
    rng=np.random.default_rng(938);s=rng.integers(1,256,size=(4,2));shift=np.stack((s//16,s%16),-1)
    raw['shift'][:]=shift[:,None,:,:]
    return raw,saved,m.extract(raw,saved)


def panel_from(one,nd=4,npilot=6):
    raw,saved,_=one;panels=[]
    for n in (nd,npilot):
        rows=[]
        for j in range(n):
            r={k:np.roll(v,j%4,axis=0) for k,v in raw.items()};old={k:np.roll(v,j%4,axis=0) for k,v in saved.items()}
            rows.append(m.extract(r,old))
        panels.append({k:np.stack([a[k] for a in rows]) for k in m.SHAPES})
    return (*panels,np.arange(90000,90000+nd,dtype=np.int64),np.arange(100000,100000+npilot,dtype=np.int64))


@pytest.fixture(scope='module')
def small(one):
    inputs=panel_from(one);return inputs,m.summarize(*inputs)


def test_one_block(one):
    raw,saved,got=one;p=c.block(raw,got,saved)
    assert p['passes'] and p['geometry_values']==832 and p['max_error']<2e-10


def test_full_panel_roundtrip(tmp_path,record_property,one,monkeypatch):
    assert run.ROOT in tmp_path.parents
    for name in ('solve','lstsq','svd'):monkeypatch.setattr(np.linalg,name,forbid)
    start=time.monotonic();raw,saved,_=one;arrays=[];proofs=[]
    for n in (16,64):
        rows=[]
        for j in range(n):
            r={k:np.roll(v,j%4,axis=0) for k,v in raw.items()};old={k:np.roll(v,j%4,axis=0) for k,v in saved.items()}
            got=m.extract(r,old);proofs.append(c.block(r,got,old));rows.append(got)
        arrays.append({k:np.stack([a[k] for a in rows]) for k in m.SHAPES})
    di=np.arange(90000,90016,dtype=np.int64);pi=np.arange(100000,100064,dtype=np.int64)
    s=m.summarize(*arrays,di,pi);proof=c.summary(s,*arrays,di,pi)
    packed={co+'_'+k:v for co,a in zip(('development','pilot'),arrays) for k,v in a.items()}
    run.io.write_npz(tmp_path/'geometry.npz',packed,run.ROOT);run.io.write_json(tmp_path/'summary.json',s,run.ROOT)
    read=run.io.load_npz(tmp_path/'geometry.npz');c.same(read,packed)
    assert c.summary(run.io.read_json(tmp_path/'summary.json'),*run.parts(read))==proof
    assert sum(p['geometry_values'] for p in proofs)==66560
    assert sum(p.stat().st_size for p in tmp_path.iterdir())<run.source.ALLOWANCE
    with pytest.raises(FileExistsError):run.io.write_npz(tmp_path/'geometry.npz',packed,run.ROOT)
    record_property('full_panel_seconds',time.monotonic()-start);record_property('founders',80)
    record_property('geometry_values',66560);record_property('summary_rows',608)


@pytest.mark.parametrize('role',[0,1])
def test_all_legal_shifts(role):
    shifts=np.asarray([divmod(j,16) for j in range(1,256)],dtype=np.int64)
    np.testing.assert_array_equal(m.ideal(shifts,role),c.ideal(shifts,role))
    assert set(m.ideal(shifts,role))==set(m.LEVELS[role])
    if role==1:assert m.ideal(np.array([[3,8]],np.int64),1)[0]==1


def test_toroidal_rotation():
    x=np.arange(256,dtype=float).reshape(16,16)
    for s in ((0,0),(15,1),(7,12)):
        np.testing.assert_array_equal(m.shifted(x,np.asarray(s,np.int64)),c.rotate(x,s))


def test_phase_reversal_is_not_shape_loss():
    b=c.prior.templates()[1];s=np.array([0,4],np.int64)
    assert m.ideal(s,1)==-1 and c.shape(c.rotate(b,s),1)==1


def test_masked_zero(one):
    _,_,a=one
    assert not a['feedback_valid'][...,0,:].any() and not a['feedback'][...,0,:].any()
    values=np.zeros((4,4,2));valid=np.zeros_like(values,bool);row=m.describe(values,valid)
    c.same(row,c.description(values,valid));assert row['copy_mean']==[None,None] and row['paired_gap'] is None
    assert row['undefined']==4 and row['numerical_zero']==0


@pytest.mark.parametrize('which',['left','right','both'])
def test_constant_correlation(which):
    a=np.arange(256,dtype=float).reshape(16,16);b=np.flip(a).copy()
    if which in ('left','both'):a[:]=3
    if which in ('right','both'):b[:]=4
    x,v=m.corr(a,b);assert x==0 and not v;assert c.correlation(a,b)==(0.,False)


def test_next_step_checkpoint(one):
    raw,saved,got=deepcopy(one)
    for life in range(4):
        for g in range(4):
            for copy in range(2):
                theta=raw['write_states'][life,g,copy,1,3];ref=raw['write_states'][life,g,copy,1,2]
                shift=raw['shift'][life,g,copy] if g%2==0 else (0,0)
                want,valid=c.correlation(c.rotate(theta,shift),ref)
                c.same(got['feedback'][life,g,copy,1,1],want);assert got['feedback_valid'][life,g,copy,1,1]==valid
    assert not got['feedback_valid'][...,0,:].any() and got['feedback_valid'][...,1,:].all()
    # A later checkpoint edit cannot be read as an earlier applied field.
    raw['write_states'][:,:,:,3,3]*=-1
    other=m.extract(raw,saved)
    np.testing.assert_array_equal(got['feedback'][...,:3,:],other['feedback'][...,:3,:])
    np.testing.assert_allclose(other['feedback'][...,3,:],-got['feedback'][...,3,:],atol=2e-10)


def test_aligned_unused_assignment(one):
    raw,saved,got=deepcopy(one);raw['shift'][:]=np.array([3,4],np.int64)
    other=m.extract(raw,saved)
    for g in (1,3):
        np.testing.assert_array_equal(other['q'][:,g,:,1],1)
        np.testing.assert_array_equal(other['feedback'][:,g],got['feedback'][:,g])
        np.testing.assert_array_equal(other['reference'][:,g,:,:,1],got['reference'][:,g,:,:,1])


def test_partial_valid_profile():
    x=np.arange(32,dtype=float).reshape(4,4,2);ok=np.ones_like(x,bool)
    ok[0]=False;ok[1,0,0]=False
    row=m.describe(x,ok);c.same(row,c.description(x,ok))
    assert row['paired_count']==11 and row['undefined']==1


def test_empty_levels():
    q=np.zeros((4,4,2));y=np.ones((4,4,2,7));rows=m.level_rows(q,y,1)
    c.same(rows,c.levels(q,y,1))
    assert len(rows)==5 and rows[0]['counts']==[0,0] and rows[0]['pooled_mean']==[None]*7
    got=m.mixture(q,y[...,0],rows,0);c.same(got,c.accounting(q,y[...,0],rows,0));assert got['gap']==got['mixture']==got['residual']==0


def test_one_copy_only_level():
    q=np.zeros((4,4,2));q[...,0]=-1;q[...,1]=1;y=np.repeat(q[...,None],7,axis=-1)
    rows=m.level_rows(q,y,1);c.same(rows,c.levels(q,y,1))
    assert rows[0]['copy_means'][1]==[None]*7 and rows[-1]['copy_means'][0]==[None]*7
    got=m.mixture(q,y[...,0],rows,0);c.same(got,c.accounting(q,y[...,0],rows,0))
    assert got['gap']==got['mixture']==2 and got['residual']==0


def test_mixture_cancellation():
    q=np.broadcast_to(np.array([[-1,-1],[-1,1],[-1,1],[1,1]],float),(4,4,2)).copy()
    y=q.copy();y[...,1]-=1;ys=np.repeat(y[...,None],7,axis=-1)
    rows=m.level_rows(q,ys,1);got=m.mixture(q,y,rows,0);c.same(got,c.accounting(q,y,rows,0))
    assert got['gap']==0 and got['mixture']>0 and got['residual']==-got['mixture']
    assert 'fraction' not in got


def test_mixture_founder_weighting():
    q=np.zeros((4,4,2));y=np.zeros((4,4,2,7));y[2,:,1]=.8
    rows=m.level_rows(q,y,0);got=m.mixture(q,y[...,0],rows,0);c.same(got,c.accounting(q,y[...,0],rows,0))
    assert got['gap']==.2 and got['mixture']==0 and got['residual']==.2
    assert got['gap_omissions']['minimum']==0 and got['pooled_reference_refit_on_omission'] is False


def test_copy_reversal(small):
    inputs,s=small;d,p,di,pi=inputs
    flipped=[{k:np.flip(v,axis=3).copy() for k,v in a.items()} for a in (d,p)]
    other=m.summarize(*flipped,di,pi);c.summary(other,*flipped,di,pi)
    for before,after in zip(s['mixture_rows'],other['mixture_rows']):
        for k in ('gap','mixture','residual'):c.same(after[k],-before[k])


def test_founder_permutation(small):
    inputs,s=small;d,p,di,pi=inputs;reordered=[{k:v[::-1].copy() for k,v in a.items()} for a in (d,p)]
    other=m.summarize(*reordered,di[::-1],pi[::-1]);c.summary(other,*reordered,di[::-1],pi[::-1])
    for before,after in zip(s['mixture_rows'],other['mixture_rows']):
        for k in ('gap','mixture','residual'):c.same(after[k],before[k])
        c.same(after['founder_gap'],before['founder_gap'][::-1])


@pytest.mark.parametrize('constant',['x','y','none'])
def test_association_moments(constant):
    rng=np.random.default_rng(183);x=rng.normal(size=(5,4));y=2*x+rng.normal(size=(5,4));valid=np.ones_like(x,bool)
    valid[0,0]=False
    if constant=='x':x[:]=.3
    if constant=='y':y[:]=.7
    got=m.association(x,valid,y);c.same(got,c.assoc(x,valid,y))
    if constant!='none':assert got['correlation'] is None


@pytest.mark.parametrize('key',list(m.SHAPES))
def test_corruption(one,key):
    raw,saved,got=deepcopy(one)
    if got[key].dtype==bool:got[key].flat[-1]=not got[key].flat[-1]
    elif got[key].dtype==np.int64:got[key].flat[-1]=(got[key].flat[-1]+1)%16
    else:got[key].flat[-1]+=.1
    with pytest.raises(AssertionError):c.block(raw,got,saved)


@pytest.mark.parametrize('kind',['profile','level','association','mixture'])
def test_summary_corruption(small,kind):
    inputs,s=deepcopy(small)
    if kind=='profile':s['profile_rows'][0]['copy_mean'][0]+=.1
    elif kind=='level':s['level_rows'][0]['counts'][0]+=1
    elif kind=='association':s['association_rows'][0]['founder_sufficient'][0][0]+=1
    else:s['mixture_rows'][0]['residual']+=.1
    with pytest.raises(AssertionError):c.summary(s,*inputs)


def test_no_outcomes_or_dynamics(one,monkeypatch):
    for module in (m,c,run):
        for node in ast.walk(ast.parse(inspect.getsource(module))):
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute):
                assert node.func.attr not in ('fit','train','solve','svd','lstsq','predict','simulate','rollout','blueprint_step',
                    'read_trace','write_trace','read_selected','write_streams','simulate_life','source_features')
    for key in ('solve','lstsq','svd'):monkeypatch.setattr(np.linalg,key,forbid)
    monkeypatch.setattr(run.previous,'source_features',forbid)
    raw,saved,_=deepcopy(one);raw['outcomes']=np.zeros(1)
    with pytest.raises(AssertionError):m.extract(raw,saved)


def test_checker_independence(one,small,monkeypatch):
    raw,saved,got=one;inputs,s=small
    for name in ('extract','corr','shifted','ideal','describe','association','level_rows','mixture','profiles','summarize'):
        monkeypatch.setattr(m,name,forbid)
    assert c.block(raw,got,saved)['passes'] and c.summary(s,*inputs)['passes']


@pytest.mark.parametrize('stage',['execute','audit'])
def test_stage_guard(monkeypatch,stage):
    monkeypatch.delenv(run.ENV,raising=False);run.stage_guard({'must_detach':False},stage)
    with pytest.raises(AssertionError):run.stage_guard({'must_detach':True},stage)
    monkeypatch.setenv(run.ENV,stage);monkeypatch.setattr(run.os,'getsid',lambda n:12);monkeypatch.setattr(run.os,'getpid',lambda:13)
    with pytest.raises(AssertionError):run.stage_guard({'must_detach':True},stage)
    monkeypatch.setattr(run.os,'getpid',lambda:12);monkeypatch.setattr(run.sys.stdin,'isatty',lambda:False)
    run.stage_guard({'must_detach':True},stage)


def test_external_write_once(tmp_path):
    assert run.ROOT in tmp_path.parents;p=tmp_path/'once.json';run.io.write_json(p,{'ok':True},run.ROOT)
    with pytest.raises(FileExistsError):run.io.write_json(p,{'ok':False},run.ROOT)
    with pytest.raises(ValueError):run.io.write_json(run.WS/'forbidden_d168_output.json',{},run.ROOT)


def test_hash_drift(tmp_path):
    p=tmp_path/'pin.json';run.io.write_json(p,{'ok':True},run.ROOT);seen={}
    with pytest.raises(AssertionError):run.source.bind(p,'0'*64,seen)
    assert not seen
