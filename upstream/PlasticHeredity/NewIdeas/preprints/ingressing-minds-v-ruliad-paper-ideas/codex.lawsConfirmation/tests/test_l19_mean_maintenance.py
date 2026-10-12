"""D102 analytic/disposable tests and known D101 bridge; no main cohort draws."""
from copy import deepcopy
from dataclasses import replace
import inspect
import os
import subprocess
import sys

import numpy as np
import pytest

from laws_confirmation import l19_mean_maintenance as p
from laws_confirmation import l19_mean_maintenance_run as run
from laws_confirmation.io import DEFAULT_EXTERNAL_ROOT as ROOT,canonical_digest

SHORT=replace(p.CONFIG,settle=4,training_cycles=1,cycles=4,teaching=3,free=4)


@pytest.fixture(scope='module')
def block(): return p.execute_block(p.DISPOSABLE,SHORT)


@pytest.fixture
def piece(block):
    raw,meta=deepcopy(block)
    return {k:v[0] for k,v in raw.items()},meta['lives'][0]


def test_fixed_design():
    assert p.TISSUES==tuple(range(47000,47008)) and p.DISPOSABLE not in p.TISSUES
    assert p.CONFIG==p.base.CONFIG and p.contract()['controller_state_bytes']==0
    assert p.ARMS==('continued','withdrawn','mean_early','mean_late','spatial_rescue')
    assert run.contract()['absolute_fidelity_gate'] is None
    assert p.contract()['fresh_branches']==80 and len(run.output_names())==19


@pytest.mark.parametrize('bad',[-1,True,1.5,'47000'])
def test_invalid_identity(bad):
    with pytest.raises(ValueError): p.context(bad)


@pytest.mark.parametrize('change',[dict(lives=0),dict(settle=-1),dict(cycles=2),
    dict(primary_cycle=2),dict(rescue_cycle=3),dict(teaching=0),dict(free=0),dict(amplitude=float('nan'))])
def test_config_validation_is_inherited(change):
    with pytest.raises(ValueError): replace(p.CONFIG,**change)


def test_analytic_projection():
    uniform=np.full((16,16),1.75)
    actual,offset=p.balance(uniform)
    np.testing.assert_array_equal(actual,0); assert offset==-1.75
    v=np.zeros((16,16)); v.flat[0]=10.
    expected=np.full((16,16),-2/255); expected.flat[0]=2.
    actual,offset=p.balance(v)
    np.testing.assert_allclose(actual,expected,rtol=0,atol=1e-14)
    assert offset==pytest.approx(-2/255,abs=1e-14)
    negative,other=p.balance(-v)
    np.testing.assert_allclose(negative,-actual,rtol=0,atol=1e-14)
    assert other==pytest.approx(-offset,abs=1e-14)


@pytest.mark.parametrize('seed',range(6))
def test_projection_bounds_and_independent_solution(seed):
    v=p.rng(p.DISPOSABLE,0,f'projection:{seed}').normal(0,3,(16,16)); saved=v.copy()
    result,shift=p.balance(v); reference,other=p.checker().project(v)
    np.testing.assert_array_equal(v,saved)
    np.testing.assert_allclose(result,reference,rtol=0,atol=1e-14)
    assert abs(result.mean())<1e-12 and np.max(abs(result))<=2
    assert shift==pytest.approx(other,abs=1e-14)
    order=np.argsort(v.ravel()); assert np.all(np.diff(result.ravel()[order])>=0)
    mask=abs(result)<2
    np.testing.assert_allclose(result[mask]-v[mask],shift,rtol=0,atol=1e-14)


def test_projection_has_no_spatial_address():
    v=p.rng(p.DISPOSABLE,0,'spatial').normal(0,2,(16,16)); result,_=p.balance(v)
    translated,_=p.balance(np.roll(v,5,axis=1))
    np.testing.assert_allclose(translated,np.roll(result,5,axis=1),rtol=0,atol=1e-14)
    shifted,_=p.balance(v+.3)
    np.testing.assert_allclose(shifted,result,rtol=0,atol=1e-14)


@pytest.mark.parametrize('value',[np.ones(16),np.ones((1,16,16)),np.ones((16,16),dtype=np.float32),
                                  np.full((16,16),np.nan),np.full((16,16),np.inf)])
def test_projection_rejects_invalid(value):
    with pytest.raises(ValueError): p.balance(value)


def test_target_blind_controller(piece):
    assert tuple(inspect.signature(p.balance).parameters)==('v',)
    class Poison:
        def copy(self): raise AssertionError('target accessed')
        def __array__(self,*args,**kwargs): raise AssertionError('target accessed')
    for arm in ('mean_early','mean_late','withdrawn'):
        assert all(teacher is None for _,teacher in p.schedule(arm,Poison(),SHORT))
    raw,_=piece; ctx=p.context(p.DISPOSABLE)
    with pytest.raises(ValueError,match='forbidden'):
        p.window(raw['training'][-1],raw['theta'],ctx,p.rng(0,0,'test'),'mean',raw['ancestor'],SHORT)


def test_no_direct_reference_or_ema_rewrite(piece,monkeypatch):
    raw,_=piece; state=raw['training'][-1].copy(); ctx=p.context(p.DISPOSABLE); seen=[]
    def identity(v,ema,ref,*args):
        seen.append((v.copy(),ema.copy(),ref.copy())); return v,ema,ref
    monkeypatch.setitem(ctx['api'],'blueprint_step',identity)
    result,_=p.window(state,raw['theta'],ctx,p.rng(0,0,'test'),'mean',None,replace(SHORT,teaching=1))
    np.testing.assert_array_equal(seen[0][1][0],state[1]); np.testing.assert_array_equal(seen[0][2][0],state[2])
    np.testing.assert_array_equal(result[1:],state[1:]); assert abs(result[0].mean())<=1e-12


def test_full_disposable_replay(block):
    raw,meta=block
    assert p.checker().check_block(raw,meta,SHORT,replay=True)
    assert all(m['replay']['max_abs']==0 for m in meta['lives'])


def test_delayed_state_trace_aliases(piece):
    raw,meta=piece
    for i in (3,4):
        np.testing.assert_array_equal(raw['states'][i,:10],raw['states'][1,:10])
        np.testing.assert_array_equal(raw['control'][i,:3],raw['control'][1,:3])
    assert not np.array_equal(raw['states'][3,-1],raw['states'][1,-1])
    assert all(x==meta['branch_rng'][0] for x in meta['branch_rng'])


def test_order_and_duplicate_aliases(piece):
    raw,meta=piece; order=('spatial_rescue','mean_late','mean_early','withdrawn','continued','mean_early')
    other,om=p.simulate_life(p.DISPOSABLE,0,SHORT,arms=order)
    for a,b in enumerate((4,3,2,1,0,2)):
        np.testing.assert_array_equal(other['states'][a],raw['states'][b])
        np.testing.assert_array_equal(other['control'][a],raw['control'][b])
        assert om['branch_rng'][a]==meta['branch_rng'][b]


def test_equal_noise_and_window_duration(piece):
    raw,meta=piece; r=p.rng(p.DISPOSABLE,0,'branch:1')
    r.integers(0,2,1); r.integers(0,2,1)
    for _ in range(1+SHORT.teaching+SHORT.free): r.standard_normal((1,16,16))
    assert all(row[0]==canonical_digest(r.bit_generator.state) for row in meta['branch_rng'])
    assert raw['control'].shape==(5,4,3,7)
    assert np.max(abs(raw['control'][2,:,:,1]))<=1e-12


def test_d101_saved_baseline_anchor():
    p.api(); out=ROOT/'outputs'/p.base.RUN_ID
    raw=run.u.load_npz(out/'block_46000.npz'); meta=run.u.read_json(out/'block_46000.json')
    assert p.base.checker().check_block(raw,meta,p.base.CONFIG,replay=True)
    ctx=p.context(46000)
    for life in range(2):
        for arm,old_id in (('continued',0),('withdrawn',1)):
            state,mask,digests,_=p.branch(raw['training'][life,-1],raw['theta'][life],ctx,46000,life,
                p.schedule(arm,raw['ancestor'][life]),tag=p.base.TAG)
            np.testing.assert_array_equal(state,raw['states'][life,old_id])
            np.testing.assert_array_equal(mask,raw['fresh'][life])
            assert digests==meta['lives'][life]['branch_rng'][old_id]


@pytest.mark.parametrize('field',['theta','ancestor','training','states','values','fresh','training_fresh'])
def test_state_corruption_rejected(piece,field):
    raw,meta=piece
    if raw[field].dtype==np.bool_: raw[field].flat[-1]=~raw[field].flat[-1]
    else: raw[field].flat[-1]+=.1
    with pytest.raises(AssertionError): p.checker().check_life(raw,meta,SHORT)


def test_controller_trace_corruption(piece):
    raw,meta=piece
    for column in range(7):
        altered=deepcopy(raw); altered['control'][2,0,0,column]+=.01
        with pytest.raises(AssertionError): p.checker().check_life(altered,meta,SHORT)


@pytest.mark.parametrize('field',['index','life','tag','config','arms','branch_rng','founder_rng','theta_writable'])
def test_metadata_corruption_rejected(piece,field):
    raw,meta=piece
    if field=='index': meta[field]+=1
    elif field=='life': meta[field]=True
    elif field=='config': meta[field]['teaching']+=1
    elif field=='arms': meta[field].reverse()
    elif field=='branch_rng': meta[field][0][0]='bad'
    elif field=='theta_writable': meta[field]=True
    else: meta[field]='bad'
    with pytest.raises(AssertionError): p.checker().check_life(raw,meta,SHORT)


def test_hand_built_primary(block):
    blocks=[deepcopy(block[0]) for _ in range(8)]
    for b in blocks:
        b['values'].fill(0); b['control'].fill(0); b['values'][:,:,3:,13]=64
        b['values'][:,2,3:,12]=48; b['values'][:,1,3:,12]=16
    summary=p.summarize(blocks,SHORT)
    assert summary['primary']['name']=='mean_early_minus_withdrawn'
    assert summary['primary']['mean']==.5 and summary['primary']['pointwise_block_bootstrap_95']==[.5,.5]
    assert summary['label']=='MEAN_ONLY_MAINTENANCE_BENEFIT'


def test_independent_pooling(block):
    assert p.checker().check_summary(p.summarize([block[0]]*8,SHORT),[block[0]]*8,SHORT)


@pytest.mark.parametrize('field',['primary','label','window_control_means','max_controlled_mean_residual','absolute_fidelity_gate'])
def test_summary_corruption_rejected(block,field):
    result=p.summarize([block[0]]*8,SHORT)
    if field=='primary': result[field]['mean']+=.01
    elif field=='label': result[field]='wrong'
    elif field=='window_control_means': result[field][2][0][0]+=.1
    elif field=='max_controlled_mean_residual': result[field]=.01
    else: result[field]=.8
    with pytest.raises(AssertionError): p.checker().check_summary(result,[block[0]]*8,SHORT)


@pytest.mark.parametrize('defect',['missing','nan','empty','unpaired','controller'])
def test_invalid_summary_input(block,defect):
    blocks=[deepcopy(block[0]) for _ in range(8)]
    if defect=='missing': blocks.pop()
    elif defect=='nan': blocks[0]['values'].flat[0]=np.nan
    elif defect=='empty': blocks[0]['values'][0,0,3,13]=0
    elif defect=='unpaired': blocks[0]['values'][0,0,3,13]+=1
    else: blocks[0]['control'][0,2,0,0,1]=.1
    with pytest.raises(ValueError): p.summarize(blocks,SHORT)


def test_saved_roundtrip_and_external_guard(block,tmp_path):
    raw,meta=block; loaded=run.u.save_pair(tmp_path,'block',raw,meta,ROOT)
    assert p.checker().check_block(loaded,run.u.read_json(tmp_path/'block.json'),SHORT,replay=False)
    with pytest.raises(FileExistsError): run.u.write_json(tmp_path/'block.json',{},ROOT)
    with pytest.raises(ValueError): run.u.write_npz(p.WS/'forbidden.npz',raw,ROOT)


def test_prior_run_not_monkeypatched():
    assert run.previous.p is p.base
    assert run.previous.contract()['decision']=='D101' and run.contract()['decision']=='D102'
    assert run.previous.contract()['fresh_branches']==64 and run.contract()['fresh_branches']==80


def test_missing_detachment_record_is_rejected(tmp_path):
    with pytest.raises(FileNotFoundError): run.detached_guard(tmp_path,True)


def test_reserved_run_is_not_reused(monkeypatch,tmp_path):
    monkeypatch.setattr(run.u,'preflight',lambda *a,**kw:None)
    monkeypatch.setattr(run,'main_inputs',lambda root:{})
    monkeypatch.setattr(run,'timing_checked',lambda root:{})
    (tmp_path/'runs'/p.RUN_ID).mkdir(parents=True)
    with pytest.raises(FileExistsError): run.prepare(tmp_path)
    assert not (tmp_path/'outputs'/p.RUN_ID).exists()


def test_fresh_process_import():
    result=subprocess.run([sys.executable,'-c','from laws_confirmation.l19_mean_maintenance import api; '
        'assert api()["teaching"].__name__=="teaching.pipeline"; print("imports only")'],
        cwd=p.WS,env=os.environ.copy(),capture_output=True,text=True,check=True)
    assert result.stdout.strip()=='imports only'
