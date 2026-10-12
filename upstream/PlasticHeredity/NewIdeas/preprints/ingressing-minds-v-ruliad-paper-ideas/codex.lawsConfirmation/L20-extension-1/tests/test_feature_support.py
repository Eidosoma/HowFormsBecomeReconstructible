"""D166 qualification with synthetic measurements, no fitted predictors/outcomes."""
import ast
from copy import deepcopy
import inspect
import time
import numpy as np
import pytest
from l20_extension1 import feature_support as m, feature_support_check as c, feature_support_run as run


def forbid(*args,**kwargs):raise AssertionError('no fitting or outcome loading')


@pytest.fixture(scope='module')
def small():
    inputs=m.fixture();arrays=m.calculate(*inputs);s=m.summarize(arrays,*inputs)
    return inputs,arrays,s


def test_full_panel_roundtrip(tmp_path,record_property,monkeypatch):
    assert run.ROOT in tmp_path.parents
    for name in ('solve','svd','lstsq'):monkeypatch.setattr(np.linalg,name,forbid)
    start=time.monotonic();inputs=m.fixture(16,64);a=m.calculate(*inputs);s=m.summarize(a,*inputs)
    proof=run.verify(a,s,inputs)
    run.io.write_npz(tmp_path/'support.npz',a,run.ROOT);run.io.write_json(tmp_path/'summary.json',s,run.ROOT)
    assert run.verify(run.io.load_npz(tmp_path/'support.npz'),run.io.read_json(tmp_path/'summary.json'),inputs)==proof
    assert proof['arrays']['nearest_distances']==366080 and proof['arrays']['scalar_case_positions']==1214720
    assert sum(p.stat().st_size for p in tmp_path.iterdir())<run.source.ALLOWANCE
    with pytest.raises(FileExistsError):run.io.write_npz(tmp_path/'support.npz',a,run.ROOT)
    record_property('full_panel_seconds',time.monotonic()-start);record_property('new_fits',0)
    record_property('scalar_rows',292);record_property('vector_rows',88)


def test_no_outcome_or_fit(small,monkeypatch):
    inputs,a,s=small
    assert list(inspect.signature(m.calculate).parameters)==['development','pilot','development_ids','pilot_ids']
    for module in (m,c,run):
        for node in ast.walk(ast.parse(inspect.getsource(module))):
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute):
                assert node.func.attr not in ('fit','train','solve','svd','lstsq','predict','simulate','rollout')
    for name in ('solve','svd','lstsq'):monkeypatch.setattr(np.linalg,name,forbid)
    assert run.verify(a,s,inputs)['passes']
    bad=deepcopy(inputs);bad[0]['labels']=np.zeros((4,4,4))
    with pytest.raises(AssertionError):m.calculate(*bad)


def test_loader_excludes_outcomes(monkeypatch):
    d,_,ids,_=m.fixture();accessed=[]
    class Archive:
        files=['start','endpoint','targeted','block_ids','labels','futures']
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def __getitem__(self,key):
            accessed.append(key)
            if key=='block_ids':return ids.copy()
            assert key in d,'forbidden outcome member';return d[key].copy()
    monkeypatch.setattr(run.np,'load',lambda *a,**kw:Archive())
    features,gotids=run.features('synthetic',True)
    assert accessed==['start','endpoint','targeted','block_ids']
    assert not any(v.flags.writeable for v in features.values()) and not gotids.flags.writeable


def test_excluded_founder(small):
    inputs,a,_=small;changed=deepcopy(inputs)
    for v in changed[0].values():v[0]+=100
    b=m.calculate(*changed)
    for key in a:
        if key.startswith('reference_'):c.same(a[key][0],b[key][0])
        if key.startswith('pilot_'):c.same(a[key][0],b[key][0])
    assert np.all(b['development_neighbor_founder'][0]!=inputs[2][0])
    assert np.all(b['development_side'][0,:,:,:13]!=0)


def test_pilot_does_not_change_reference(small):
    inputs,a,_=small;changed=deepcopy(inputs)
    for v in changed[1].values():v*=10;v+=20
    b=m.calculate(*changed)
    for key in a:
        if key.startswith(('full_','reference_','development_')) or key=='active_dimensions':c.same(a[key],b[key])


def test_constant_dimensions():
    inputs=m.fixture()
    for f in inputs[:2]:
        for v in f.values():v[:]=.7
    inputs[1]['start'][0,0,0,0]=.8
    a=m.calculate(*inputs);s=m.summarize(a,*inputs);assert run.verify(a,s,inputs)['passes']
    assert not a['reference_active'].any() and not a['active_dimensions'].any()
    assert not a['pilot_distance'].any() and a['pilot_box'].any()
    row=s['scalar_rows'][0];assert row['standardized_mean_shift'] is None and row['pilot']['standardized_mean'] is None
    assert row['pilot']['above']>0 and row['pilot']['standardized_instances']==0


def test_inclusive_boundaries():
    train=np.array([[0.,2.],[1.,2.]])
    z,side=m.position(train,m.stats(train));np.testing.assert_array_equal(side,0);np.testing.assert_array_equal(z[:,1],0)
    _,side=m.position(np.array([[-.1,2.],[1.1,3.]]),m.stats(train))
    np.testing.assert_array_equal(side,[[-1,0],[1,1]])


def test_tie_order_and_distance():
    train=np.array([[0.,0.],[2.,0.]]);identity=np.array([[4,0,0],[9,0,0]],dtype=np.int64)
    dist,box,who,n=m.nearest(np.array([[1.,0.],[3.,1.]]),train,identity)
    c.same(dist,np.array([1.,1.]));np.testing.assert_array_equal(who[:,0],[4,9]);np.testing.assert_array_equal(box,[False,True]);assert n==1


def test_pooled_reference(small):
    inputs,_,_=small;d=deepcopy(inputs[0]);d['endpoint'][...,1,:]=0;d['targeted'][...,1,:]=10;d['targeted'][...,2,:]=-10
    v=m.vectors(d);own=next(x for x in m.view_specs() if x['name']=='own:separate:passive')
    shared=next(x for x in m.view_specs() if x['name']=='shared:separate:passive')
    tr,ids=m.reference(v,own,np.array([1,2,3]),inputs[2],0);pool,pids=m.reference(v,shared,np.array([3,1,2]),inputs[2],0)
    assert len(tr)==12 and len(pool)==36
    np.testing.assert_array_equal(pool[:,13],np.tile([0,10,-10],12))
    assert pids[:3].tolist()==[[90001,0,0],[90001,0,1],[90001,0,2]]
    c.same(m.stats(pool)['mean'][13],0);assert m.stats(tr)['active'][13]==False and m.stats(pool)['active'][13]


def test_two_copy_isolation(small):
    inputs,a,_=small;changed=deepcopy(inputs);changed[1]['targeted'][...,2,:]+=5
    b=m.calculate(*changed)
    unaffected=[j for j,k in enumerate(m.SCALARS) if ':sham_minus:' not in k]
    c.same(a['pilot_z'][...,unaffected],b['pilot_z'][...,unaffected])
    for j,spec in enumerate(m.view_specs()):
        if spec['condition']!='sham_minus':c.same(a['pilot_distance'][...,j],b['pilot_distance'][...,j])


def test_permutations(small):
    inputs,a,_=small;d,p,di,pi=inputs;do=np.array([2,0,3,1]);po=np.array([4,1,3,0,2]);go=np.array([2,0,3,1])
    b=m.calculate({k:v[do][:,:,go] for k,v in d.items()},{k:v[po][:,:,go] for k,v in p.items()},di[do],pi[po])
    c.same(b['development_z'],a['development_z'][do][:,:,go])
    c.same(b['pilot_z'],a['pilot_z'][do][:,po][:,:,:,go])
    c.same(b['pilot_distance'],a['pilot_distance'][do][:,po][:,:,:,go])
    np.testing.assert_array_equal(b['pilot_neighbor_founder'],a['pilot_neighbor_founder'][do][:,po][:,:,:,go])


def test_affine_units(small):
    inputs,a,_=small;changed=deepcopy(inputs)
    for f in changed[:2]:
        for v in f.values():v*=2;v+=3
    b=m.calculate(*changed)
    for co in ('development','pilot'):
        c.same(a[co+'_z'],b[co+'_z']);c.same(a[co+'_distance'],b[co+'_distance'])
        np.testing.assert_array_equal(a[co+'_side'],b[co+'_side'])
        np.testing.assert_array_equal(a[co+'_box'],b[co+'_box'])


@pytest.mark.parametrize('kind',['extra','nan','dtype','shape','duplicate','id_dtype','cross_cohort','missing','too_small'])
def test_bad_input(small,kind):
    inputs,_,_=deepcopy(small);d,p,di,pi=inputs
    if kind=='extra':d['future_seed']=np.zeros(4)
    elif kind=='nan':p['start'][0,0,0,0]=np.nan
    elif kind=='dtype':d['endpoint']=d['endpoint'].astype(np.float32)
    elif kind=='shape':p['targeted']=p['targeted'][...,:2,:]
    elif kind=='duplicate':di[0]=di[1]
    elif kind=='id_dtype':inputs=(d,p,di.astype(float),pi)
    elif kind=='cross_cohort':pi[0]=di[0]
    elif kind=='missing':d.pop('start')
    elif kind=='too_small':inputs=({k:v[:2] for k,v in d.items()},p,di[:2],pi)
    with pytest.raises(AssertionError):m.calculate(*inputs)


@pytest.mark.parametrize('kind',['reference','z','side','neighbor','distance','box','active','summary','range','count','outcome','prospective'])
def test_corruption(small,kind):
    inputs,a,s=deepcopy(small)
    if kind=='reference':a['reference_sd'][0,0,0]*=2
    elif kind=='z':a['pilot_z'][0,0,0,0,0]+=.1
    elif kind=='side':a['development_side'][0,0,0,0]=2
    elif kind=='neighbor':a['pilot_neighbor_founder'][0,0,0,0]=90000
    elif kind=='distance':a['pilot_distance'][0,0,0,0]+=.1
    elif kind=='box':a['pilot_box'][0,0,0,0,0]=not a['pilot_box'][0,0,0,0,0]
    elif kind=='active':a['active_dimensions'][0,0,0]=0
    elif kind=='summary':s['scalar_rows'][0]['pilot']['outside']+=.1
    elif kind=='range':s['scalar_rows'][0]['development_raw']['minimum']-=1
    elif kind=='count':s['pilot_founders']*=4
    elif kind=='outcome':s['outcomes_used']=True
    elif kind=='prospective':s['prospective_evidence']=True
    with pytest.raises(AssertionError):run.verify(a,s,inputs)


def test_quantile():
    x=np.array([1.,4.,6.,8.]);assert c.quantile(x,.5)==5 and c.quantile(x,.9)==7.4


def test_stage_guard(monkeypatch):
    monkeypatch.delenv(run.ENV,raising=False);run.stage_guard(dict(must_detach=False),'execute')
    with pytest.raises(AssertionError):run.stage_guard(dict(must_detach=True),'execute')
    monkeypatch.setenv(run.ENV,'execute');monkeypatch.setattr(run.os,'getsid',lambda _:1);monkeypatch.setattr(run.os,'getpid',lambda:2)
    with pytest.raises(AssertionError):run.stage_guard(dict(must_detach=True),'execute')


def test_source_hash_corruption(tmp_path):
    path=tmp_path/'source.json';run.io.write_json(path,dict(synthetic=True),run.ROOT)
    run.source.check_hashes(run.io.hashes([path]))
    with pytest.raises(AssertionError):run.source.check_hashes({str(path):'0'*64})
