"""D103 disposable controls and known D102 anchor; no fresh main seed draws."""
from copy import deepcopy
from dataclasses import replace
import inspect
import os
import subprocess
import sys

import numpy as np
import pytest

from laws_confirmation import l19_reference_protection as p
from laws_confirmation import l19_reference_protection_run as run
from laws_confirmation.io import DEFAULT_EXTERNAL_ROOT as ROOT,canonical_digest

SHORT=replace(p.CONFIG,settle=4,training_cycles=1,cycles=4,primary_cycle=4,teaching=3,free=4)


@pytest.fixture(scope='module')
def block(): return p.execute_block(p.DISPOSABLE,SHORT)


@pytest.fixture
def piece(block):
    raw,meta=deepcopy(block)
    return {k:v[0] for k,v in raw.items()},meta['lives'][0]


def test_fixed_design():
    assert p.TISSUES==tuple(range(48000,48008)) and p.DISPOSABLE not in p.TISSUES
    assert p.CONFIG.primary_cycle==p.CONFIG.cycles==6
    assert p.ARMS==('live_on','held_on','wrong_on','live_off','held_off','wrong_off','spatial_on')
    assert p.balance is p.base.balance and p.contract()['reference_bytes']==2048
    assert run.contract()['absolute_fidelity_gate'] is None
    assert p.contract()['fresh_branches']==112 and len(run.output_names())==19


@pytest.mark.parametrize('bad',[-1,True,1.5,'48000'])
def test_invalid_identity(bad):
    with pytest.raises(ValueError): p.context(bad)


@pytest.mark.parametrize('change',[dict(lives=0),dict(settle=-1),dict(cycles=2),dict(primary_cycle=2),
    dict(primary_cycle=7),dict(teaching=0),dict(free=0),dict(shift=16),dict(amplitude=float('nan')),
    dict(amp_threshold=2),dict(training_cycles=True)])
def test_config_validation(change):
    with pytest.raises(ValueError): replace(p.CONFIG,**change)


@pytest.mark.parametrize('arm',p.ARMS)
def test_arm_configuration_is_local(piece,arm):
    raw,_=piece; initial=raw['training'][-1]; saved=initial.copy(); ctx=p.context(p.DISPOSABLE)
    state,changed,mode=p.configured(initial,ctx,arm,SHORT)
    _,rho,gain,record,expected_mode=p.CASES[p.ARMS.index(arm)]
    assert changed['bp'].rho==rho and changed['bp'].c_m==gain and mode==expected_mode
    assert ctx['bp'].rho==.002 and ctx['bp'].c_m==.2
    np.testing.assert_array_equal(initial,saved); np.testing.assert_array_equal(state[:2],initial[:2])
    expected=np.roll(initial[2],8,axis=-1) if record=='shifted' else initial[2]
    np.testing.assert_array_equal(state[2],expected)
    assert not np.shares_memory(state,initial)


def test_wrong_record_matched(piece):
    raw,_=piece; trained=raw['training'][-1,2]; wrong=raw['states'][2,0,2]
    assert not np.array_equal(trained,wrong)
    np.testing.assert_array_equal(np.sort(trained,axis=None),np.sort(wrong,axis=None))
    assert trained.mean()==pytest.approx(wrong.mean(),abs=1e-14)
    assert np.linalg.norm(trained)==pytest.approx(np.linalg.norm(wrong),abs=1e-14)
    for axis in (0,1):
        assert np.mean((trained-np.roll(trained,1,axis))**2)==pytest.approx(
            np.mean((wrong-np.roll(wrong,1,axis))**2),abs=1e-14)


def test_protected_record_immutable(piece):
    raw,_=piece
    for ai in (1,2,4,5):
        for state in raw['states'][ai]: np.testing.assert_array_equal(state[2],raw['states'][ai,0,2])
    assert not np.array_equal(raw['states'][0,-1,2],raw['states'][0,0,2])


def test_reader_off_aliases(piece):
    raw,meta=piece
    for ai in (4,5):
        np.testing.assert_array_equal(raw['states'][ai,:,:2],raw['states'][3,:,:2])
        np.testing.assert_array_equal(raw['control'][ai],raw['control'][3])
        assert meta['branch_rng'][ai]==meta['branch_rng'][3]
    assert not np.array_equal(raw['states'][4,:,2],raw['states'][5,:,2])


def test_target_exclusion(piece):
    raw,_=piece; ctx=p.context(p.DISPOSABLE)
    assert tuple(inspect.signature(p.balance).parameters)==('v',)
    class Poison:
        def __array__(self,*args,**kwargs): raise AssertionError('target accessed')
    for arm in p.ARMS[:6]:
        with pytest.raises(ValueError,match='forbidden'):
            p.branch(raw['training'][-1],raw['theta'],ctx,p.DISPOSABLE,0,arm,SHORT,teacher=Poison())
    with pytest.raises(ValueError,match='required'):
        p.branch(raw['training'][-1],raw['theta'],ctx,p.DISPOSABLE,0,'spatial_on',SHORT)


def test_full_disposable_replay(block):
    raw,meta=block; assert p.checker().check_block(raw,meta,SHORT,replay=True)
    assert all(m['replay']['max_abs']==0 for m in meta['lives'])


def test_reverse_order_and_duplicate_aliases(piece):
    raw,meta=piece; order=p.ARMS[::-1]+('held_on',)
    other,om=p.simulate_life(p.DISPOSABLE,0,SHORT,arms=order)
    for a,arm in enumerate(order):
        b=p.ARMS.index(arm)
        np.testing.assert_array_equal(other['states'][a],raw['states'][b])
        np.testing.assert_array_equal(other['control'][a],raw['control'][b])
        assert om['branch_rng'][a]==meta['branch_rng'][b]


def test_equal_noise_and_clocks(piece):
    raw,meta=piece; random=p.rng(p.DISPOSABLE,0,'branch:1')
    random.integers(0,2,1); random.integers(0,2,1)
    for _ in range(1+SHORT.teaching+SHORT.free): random.standard_normal((1,16,16))
    assert all(row[0]==canonical_digest(random.bit_generator.state) for row in meta['branch_rng'])
    assert raw['control'].shape==(7,4,3,7)
    assert np.max(abs(raw['control'][:6,:,:,1]))<=1e-12


def test_d102_saved_baseline_anchor():
    p.api(); out=ROOT/'outputs'/p.base.RUN_ID
    raw=run.u.load_npz(out/'block_47000.npz'); meta=run.u.read_json(out/'block_47000.json')
    assert p.base.checker().check_block(raw,meta,p.base.CONFIG,replay=True)
    ctx=p.context(47000)
    for life in range(2):
        for arm,old_id in (('live_on',2),('spatial_on',0)):
            states,mask,digests,trace=p.branch(raw['training'][life,-1],raw['theta'][life],ctx,47000,life,
                arm,tag=p.base.TAG,teacher=raw['ancestor'][life] if arm=='spatial_on' else None)
            np.testing.assert_array_equal(states,raw['states'][life,old_id])
            np.testing.assert_array_equal(mask,raw['fresh'][life])
            np.testing.assert_array_equal(trace,raw['control'][life,old_id])
            assert digests==meta['lives'][life]['branch_rng'][old_id]


@pytest.mark.parametrize('field',['theta','ancestor','training','states','values','fresh','training_fresh'])
def test_state_corruption_rejected(piece,field):
    raw,meta=piece
    if raw[field].dtype==np.bool_: raw[field].flat[-1]=~raw[field].flat[-1]
    else: raw[field].flat[-1]+=.1
    with pytest.raises(AssertionError): p.checker().check_life(raw,meta,SHORT)


def test_hand_built_primary(block):
    blocks=[deepcopy(block[0]) for _ in range(8)]
    for b in blocks:
        b['values'].fill(0); b['control'].fill(0); b['values'][:,:,3:,13]=64
        b['values'][:,1,3:,12]=48; b['values'][:,0,3:,12]=16
    summary=p.summarize(blocks,SHORT)
    assert summary['primary']['name']=='held_on_minus_live_on' and summary['primary']['cycle']==4
    assert summary['primary']['mean']==.5 and summary['primary']['pointwise_block_bootstrap_95']==[.5,.5]
    assert summary['label']=='PROTECTED_REFERENCE_RETENTION_BENEFIT'


def test_independent_pooling(block):
    assert p.checker().check_summary(p.summarize([block[0]]*8,SHORT),[block[0]]*8,SHORT)


@pytest.mark.parametrize('field',['primary','label','content_contrast','record_diagnostics',
    'window_control_means','max_controlled_mean_residual','absolute_fidelity_gate'])
def test_summary_corruption_rejected(block,field):
    result=p.summarize([block[0]]*8,SHORT)
    if field in ('primary','content_contrast'): result[field]['mean']+=.01
    elif field=='label': result[field]='wrong'
    elif field=='record_diagnostics': result[field][0][0]['spatial_mae']+=.1
    elif field=='window_control_means': result[field][1][0][0]+=.1
    elif field=='max_controlled_mean_residual': result[field]=.01
    else: result[field]=.8
    with pytest.raises(AssertionError): p.checker().check_summary(result,[block[0]]*8,SHORT)


@pytest.mark.parametrize('defect',['missing','nan','empty','unpaired','controller'])
def test_invalid_summary_input(block,defect):
    blocks=[deepcopy(block[0]) for _ in range(8)]
    if defect=='missing': blocks.pop()
    elif defect=='nan': blocks[0]['values'].flat[0]=np.nan
    elif defect=='empty': blocks[0]['values'][0,0,4,13]=0
    elif defect=='unpaired': blocks[0]['values'][0,0,4,13]+=1
    else: blocks[0]['control'][0,1,0,0,1]=.1
    with pytest.raises(ValueError): p.summarize(blocks,SHORT)


def test_saved_roundtrip_and_external_guard(block,tmp_path):
    raw,meta=block; loaded=run.u.save_pair(tmp_path,'block',raw,meta,ROOT)
    assert p.checker().check_block(loaded,run.u.read_json(tmp_path/'block.json'),SHORT,replay=False)
    with pytest.raises(FileExistsError): run.u.write_json(tmp_path/'block.json',{},ROOT)
    with pytest.raises(ValueError): run.u.write_npz(p.WS/'forbidden.npz',raw,ROOT)


def test_prior_run_not_monkeypatched():
    assert run.previous.p is p.base
    assert run.previous.contract()['decision']=='D102' and run.contract()['decision']=='D103'
    assert run.previous.contract()['fresh_branches']==80 and run.contract()['fresh_branches']==112


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
    result=subprocess.run([sys.executable,'-c','from laws_confirmation.l19_reference_protection import api; '
        'assert callable(api()["blueprint_step"])'],cwd=p.WS,env=os.environ.copy(),capture_output=True,text=True,timeout=30)
    assert result.returncode==0,result.stderr


@pytest.mark.parametrize('defect',['held_R','wrong_R','off_V','off_EMA','off_trace'])
def test_reference_and_lesion_corruption_rejected_without_replay(piece,defect):
    raw,meta=piece
    if defect=='held_R': raw['states'][1,4,2,0,0]+=.1
    elif defect=='wrong_R': raw['states'][2,:,2]=raw['states'][1,:,2]
    elif defect=='off_V': raw['states'][4,4,0,0,0]+=.1
    elif defect=='off_EMA': raw['states'][5,4,1,0,0]+=.1
    else: raw['control'][4,0,1,3]+=.1
    with pytest.raises(AssertionError): p.checker().check_life(raw,meta,SHORT,replay=False)


@pytest.mark.parametrize('column',range(7))
def test_controller_trace_corruption(piece,column):
    raw,meta=piece; raw['control'][1,0,0,column]+=.01
    with pytest.raises(AssertionError): p.checker().check_life(raw,meta,SHORT)


@pytest.mark.parametrize('field',['index','life','tag','config','arms','branch_rng','founder_rng','theta_writable','arm_parameters'])
def test_metadata_corruption_rejected(piece,field):
    raw,meta=piece
    if field=='index': meta[field]+=1
    elif field=='life': meta[field]=True
    elif field=='config': meta[field]['teaching']+=1
    elif field=='arms': meta[field].reverse()
    elif field=='branch_rng': meta[field][0][0]='bad'
    elif field=='arm_parameters': meta[field][1][1]=.002
    else: meta[field]='bad'
    with pytest.raises(AssertionError): p.checker().check_life(raw,meta,SHORT)
