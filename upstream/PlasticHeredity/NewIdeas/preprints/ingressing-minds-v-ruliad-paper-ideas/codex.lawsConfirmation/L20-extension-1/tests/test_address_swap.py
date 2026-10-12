"""D169 disposable replay and adversarial qualification; no main interventions."""
from copy import deepcopy
import ast
import inspect
import json
import os
import time
import numpy as np
import pytest
from l20_extension1 import address_swap as m, address_swap_check as c, address_swap_run as run


def forbid(*args,**kwargs):raise AssertionError('forbidden production/outcome/fit call')


@pytest.fixture(scope='module')
def source():
    pins=run.source_inputs()
    for p in run.raw_paths('disposable',514240):assert pins[str(p)]==run.source.sha256_file(p)
    return run.load_source('disposable',514240)


@pytest.fixture(scope='module')
def one(source):
    tick=time.monotonic();raw,meta=source
    got,entry,proof=run.checked_life(raw,meta,'disposable',514240,0)
    return got,entry,proof,time.monotonic()-tick


def test_complete_disposable_life(one,record_property):
    raw,entry,proof,seconds=one
    assert proof['passes'] and proof['full_physics_replayed'] and proof['writer_paths']==16
    assert proof['original_paths_reproduced']==8 and proof['aligned_swap_aliases']==4
    record_property('complete_life_seconds',seconds);record_property('writer_paths',16)


def test_original_reproduction(one,source):
    raw,meta,_,_=one;old,om=source
    for g in range(4):
        for copy in range(2):
            for key in ('write_states','terminal_states','outgoing','terminal_packet'):
                np.testing.assert_array_equal(raw[key][g,copy,copy],old[key][0,g,copy])


def test_aligned_control(one):
    raw=one[0]
    for g in (1,3):
        for k in ('write_states','terminal_states','outgoing','terminal_packet','scores','response'):
            np.testing.assert_array_equal(raw[k][g,:,0],raw[k][g,:,1])


def test_step_one_and_birth_aliases(one):
    raw=one[0]
    np.testing.assert_array_equal(raw['write_states'][:,:,0,:2],raw['write_states'][:,:,1,:2])
    np.testing.assert_array_equal(raw['write_states'][:,:,:,0,3],0)
    np.testing.assert_array_equal(raw['terminal_states'][:,:,0,0],raw['terminal_states'][:,:,1,0])
    assert not np.array_equal(raw['terminal_states'][:,0,0,0],raw['terminal_states'][:,1,0,0])


def test_donor_does_not_own_noise(one,source):
    raw,meta,_,_=one;original=source[1]['lives'][0]
    for cell in meta['cells']:
        g=meta['cells'].index(cell)//4;copy=cell['body_copy']
        assert cell['writer']['noise_rng']==original['cycles'][g][copy]['writer']['noise_rng']
        assert cell['reader']['birth_rng']==original['cycles'][g][copy]['terminal_reader']['birth_rng']
        assert cell['reader']['read_rng']==original['cycles'][g][copy]['terminal_reader']['read_rng']


def test_order_invariance(one,source):
    original=run.life_source(source[0],0)
    r,e=m.simulate_life(original['read_states'][:,:,-1],original['shift'],original['guide'],
        'disposable',514240,0,order=tuple(reversed(m.CELLS)))
    for key in r:np.testing.assert_array_equal(r[key],one[0][key])
    c.same(e,one[1])


def test_checker_independence(one,source,monkeypatch):
    for name in ('simulate_life','response','best','draw','tag','contrasts','describe','summarize'):
        monkeypatch.setattr(m,name,forbid)
    for name in ('write_streams','read_selected','route','context','generator'):
        monkeypatch.setattr(m.old,name,forbid)
    proof=c.check_life(one[0],one[1],run.life_source(source[0],0),source[1]['lives'][0],True)
    c.same(proof,one[2])


@pytest.mark.parametrize('key',list(m.SHAPES))
def test_corruption(one,source,key):
    raw,meta,_,_=deepcopy(one)
    if raw[key].dtype==np.uint8:raw[key].flat[-1]^=1
    elif raw[key].dtype==np.int64:raw[key].flat[-1]=(raw[key].flat[-1]+1)%16
    else:raw[key].flat[-1]+=.03
    with pytest.raises(AssertionError):c.check_life(raw,meta,run.life_source(source[0],0),source[1]['lives'][0],key in ('write_states','terminal_states'))


@pytest.mark.parametrize('which',['noise_owner','address_owner','seed_tag','host','guide_access'])
def test_metadata_corruption(one,source,which):
    raw,meta,_,_=deepcopy(one)
    if which=='noise_owner':meta['cells'][1]['writer']['noise_rng']=meta['cells'][2]['writer']['noise_rng']
    elif which=='address_owner':meta['cells'][1]['address_donor']=0
    elif which=='seed_tag':meta['tag']='wrong'
    elif which=='host':meta['host']['tissue']['sigma']+=.1
    else:meta['cells'][1]['writer']['guide_access']=True
    with pytest.raises(AssertionError):c.check_life(raw,meta,run.life_source(source[0],0),source[1]['lives'][0],False)


@pytest.mark.parametrize('y',[
    [[0.,1.],[0.,1.]], [[0.,0.],[1.,1.]], [[0.,1.],[1.,0.]], [[.3,.3],[.3,.3]], [[.2,.8],[-.7,.6]]])
def test_factorial_identity(y):
    x=np.array(y);got=m.contrasts(x);c.same(got.tolist(),c.effects(x))
    assert abs(got[0]-got[2]-got[3])<1e-12 and abs(got[1]-got[3]+got[2])<1e-12
    assert got[2]==(got[5]+got[6])/2


def panels(one,nd=4,npilot=6):
    y=one[0]['response'];q=one[0]['q'];out={}
    for co,n in (('development',nd),('pilot',npilot)):
        values=np.broadcast_to(y,(n,4)+y.shape).copy()
        values[:,:,0,0,1,4]+=np.arange(n)[:,None]*.001
        out[co]=dict(response=values,q=np.broadcast_to(q,(n,4)+q.shape).copy())
    return out,{'development':list(range(90000,90000+nd)),'pilot':list(range(100000,100000+npilot))}


@pytest.fixture(scope='module')
def small(one):
    a,ids=panels(one);return a,ids,m.summarize(a,ids)


def test_full_panel_accounting(one,tmp_path):
    a,ids=panels(one,16,64);s=m.summarize(a,ids);proof=c.check_summary(s,a,ids)
    assert proof['rows']==56 and proof['q_pair_rows']==424
    run.io.write_json(tmp_path/'synthetic_summary.json',s,run.ROOT)
    assert c.check_summary(run.io.read_json(tmp_path/'synthetic_summary.json'),a,ids)==proof


def test_independent_summary(small,monkeypatch):
    a,ids,s=small
    for name in ('contrasts','describe','summarize'):monkeypatch.setattr(m,name,forbid)
    assert c.check_summary(s,a,ids)['passes']


@pytest.mark.parametrize('which',['mean','founder','bootstrap','support','interaction'])
def test_summary_corruption(small,which):
    a,ids,s=deepcopy(small)
    if which=='mean':s['rows'][0]['cell_mean'][0][0]+=.1
    elif which=='founder':s['rows'][0]['contrasts']['address']['founder_values'][0]+=.1
    elif which=='bootstrap':s['rows'][0]['contrasts']['address']['pointwise_founder_bootstrap_95'][0]+=.1
    elif which=='support':s['q_pair_rows'][0]['cases']+=1
    else:s['rows'][0]['contrasts']['interaction']['mean']+=.1
    with pytest.raises(AssertionError):c.check_summary(s,a,ids)


def test_empty_pair_support(small):
    a,ids,s=small
    rows=[r for r in s['q_pair_rows'] if r['cases']==0]
    assert rows and all(r['contrast_means']==[[None]*7 for _ in range(7)] for r in rows)
    for co in ids:
        for g in m.GROUPS:assert sum(r['cases'] for r in s['q_pair_rows'] if (r['cohort'],r['group'])==(co,g))==len(ids[co])*4


def test_founder_not_cell_resampling():
    v=np.array([0.,0.,0.,4.]);draws=np.random.default_rng(83).integers(0,4,(20000,4))
    d=m.describe(v,draws);assert d['mean']==1 and d['omission_minimum']==0
    weights=np.stack([np.bincount(row,minlength=4) for row in draws]);c.same(d,c.describe(v.tolist(),weights))


@pytest.mark.parametrize('wrong',[[[1.,2.],[3.,4.01]],[[1.,2.,3.],[4.,5.,6.]],
    [[1.,2.],[3.,None]],[[1.,2.],[3.,float('nan')]],[[1.,2.],[3.,float('inf')]]])
def test_numeric_structure_corruption(wrong):
    with pytest.raises(AssertionError):c.same({'matrix':wrong},{'matrix':[[1.,2.],[3.,4.]]})


def test_permutation(small):
    a,ids,s=small
    rev={co:{k:v[::-1].copy() for k,v in x.items()} for co,x in a.items()};ri={co:list(reversed(v)) for co,v in ids.items()}
    out=m.summarize(rev,ri);c.check_summary(out,rev,ri)
    for left,right in zip(s['rows'],out['rows']):
        for k in m.CONTRASTS:
            c.same(left['contrasts'][k]['mean'],right['contrasts'][k]['mean'])
            c.same(left['contrasts'][k]['founder_values'][::-1],right['contrasts'][k]['founder_values'])


def test_outcome_isolation(one,monkeypatch):
    for k in ('solve','lstsq','svd'):monkeypatch.setattr(np.linalg,k,forbid)
    for module in (m,c,run):
        for node in ast.walk(ast.parse(inspect.getsource(module))):
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute):
                assert node.func.attr not in ('fit','train','predict','source_features','source_data','simulate','descendant','generate_founders')
    raw=deepcopy(one[0]);raw['actual_outcomes']=np.ones(1)
    with pytest.raises(AssertionError):m.validate(raw)
    assert tuple(inspect.signature(m.simulate_life).parameters)==('start','shift','guide','co','index','life','order')


def test_roundtrip(one,tmp_path):
    assert run.ROOT in tmp_path.parents
    p=tmp_path/'life.npz';run.io.write_npz(p,one[0],run.ROOT)
    read=run.io.load_npz(p)
    for k in read:np.testing.assert_array_equal(read[k],one[0][k])
    with pytest.raises(FileExistsError):run.io.write_npz(p,one[0],run.ROOT)
    with pytest.raises(ValueError):run.io.write_json(run.WS/'forbidden_d169.json',{},run.ROOT)


@pytest.mark.parametrize('stage',['benchmark','execute','audit'])
def test_stage_guard(stage,monkeypatch):
    monkeypatch.delenv(run.ENV,raising=False);run.stage_guard(False,stage)
    with pytest.raises(AssertionError):run.stage_guard(True,stage)
    monkeypatch.setenv(run.ENV,stage);monkeypatch.setattr(run.os,'getsid',lambda _:10);monkeypatch.setattr(run.os,'getpid',lambda:11)
    with pytest.raises(AssertionError):run.stage_guard(True,stage)
    monkeypatch.setattr(run.os,'getpid',lambda:10)
    monkeypatch.setattr(run.os,'readlink',lambda p:'/dev/null' if p.endswith('/0') else str(run.log_path(stage)))
    run.stage_guard(True,stage)


def test_startup_ack(monkeypatch):
    read_fd,write_fd=os.pipe();monkeypatch.setenv(run.READY,str(write_fd))
    try:
        run.ready('execute');r=json.loads(os.read(read_fd,4096))
        assert r==dict(stage='execute',pid=os.getpid(),status='STARTED') and run.READY not in os.environ
    finally:os.close(read_fd)


def test_no_successor_or_polling():
    tree=ast.parse(inspect.getsource(run))
    for node in ast.walk(tree):
        if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute):assert node.func.attr not in ('sleep','poll','wait')
    assert run.WORKERS==6 and len(run.expected_outputs(run.ROOT/'outputs'/'synthetic'))==163


def test_hash_drift(tmp_path):
    p=tmp_path/'pin.json';run.io.write_json(p,{'ok':True},run.ROOT)
    with pytest.raises(AssertionError):run.source.bind(p,'0'*64,{})


@pytest.mark.parametrize('co,index',[('development',100000),('pilot',90000),('disposable',90000)])
def test_wrong_cohort(co,index):
    with pytest.raises(AssertionError):m.tag(co,index)
