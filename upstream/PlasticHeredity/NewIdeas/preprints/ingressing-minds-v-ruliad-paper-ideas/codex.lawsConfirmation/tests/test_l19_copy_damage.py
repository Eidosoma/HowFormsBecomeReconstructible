"""D104 disposable tests and known D103 anchor, never fresh main seed draws."""
from copy import deepcopy
from dataclasses import replace
import inspect
import os
import subprocess
import sys

import numpy as np
import pytest

from laws_confirmation import l19_copy_damage as p
from laws_confirmation import l19_copy_damage_run as run
from laws_confirmation.io import DEFAULT_EXTERNAL_ROOT as ROOT,canonical_digest

SHORT=replace(p.CONFIG,settle=4,training_cycles=1,teaching=3,free=4)


@pytest.fixture(scope='module')
def block(): return p.execute_block(p.DISPOSABLE,SHORT)


@pytest.fixture
def piece(block):
    raw,meta=deepcopy(block)
    return {k:v[0] for k,v in raw.items()},meta['lives'][0]


def test_fixed_design():
    assert p.TISSUES==tuple(range(49000,49008)) and p.DISPOSABLE not in p.TISSUES
    assert p.CONFIG.primary_cycle==p.CONFIG.cycles==6 and p.CONFIG.rescue_cycle==4
    assert p.CONFIG.damage_pairs==32
    assert p.ARMS==('clean_on','damaged_on','rescue_on','clean_off','damaged_off','rescue_off')
    assert p.balance is p.base.balance and p.contract()['reference_bytes']==2048
    assert run.contract()['absolute_fidelity_gate'] is None and not p.contract()['rescue_is_autonomous']
    assert p.contract()['fresh_branches']==96 and len(run.output_names())==19


@pytest.mark.parametrize('bad',[-1,True,1.5,'49000'])
def test_invalid_identity(bad):
    with pytest.raises(ValueError): p.context(bad)


@pytest.mark.parametrize('change',[dict(lives=0),dict(settle=-1),dict(cycles=2),dict(primary_cycle=2),
    dict(primary_cycle=7),dict(teaching=0),dict(free=0),dict(shift=16),dict(amplitude=float('nan')),
    dict(amp_threshold=2),dict(training_cycles=True),dict(damage_pairs=0),dict(damage_pairs=129),
    dict(damage_pairs=True),dict(rescue_cycle=3),dict(rescue_cycle=7),dict(rescue_cycle=True)])
def test_config_validation(change):
    with pytest.raises(ValueError): replace(p.CONFIG,**change)


def test_hand_built_copy_and_no_mutation():
    ref=np.arange(256,dtype=np.float64).reshape(16,16); saved=ref.copy()
    mapping=np.arange(256,dtype=np.int64); mapping[0],mapping[255]=255,0
    copied=p.copy_reference(ref,mapping,True)
    assert copied[0,0]==255 and copied[-1,-1]==0
    np.testing.assert_array_equal(copied.flat[1:255],ref.flat[1:255])
    np.testing.assert_array_equal(p.copy_reference(copied,mapping,True),ref)
    np.testing.assert_array_equal(p.copy_reference(ref,mapping,False),ref)
    np.testing.assert_array_equal(ref,saved); assert not np.shares_memory(copied,ref)


@pytest.mark.parametrize('defect',['missing','duplicate','out_of_range','float_map','not_involution',
    'nan_ref','float32_ref','bad_flag'])
def test_copy_input_rejected(defect):
    ref=np.ones((16,16),dtype=np.float64); mapping=np.arange(256,dtype=np.int64); flag=True
    if defect=='missing': mapping=mapping[:-1]
    elif defect=='duplicate': mapping[0]=1
    elif defect=='out_of_range': mapping[0]=256
    elif defect=='float_map': mapping=mapping.astype(float)
    elif defect=='not_involution': mapping[:3]=[1,2,0]
    elif defect=='nan_ref': ref[0,0]=np.nan
    elif defect=='float32_ref': ref=ref.astype(np.float32)
    else: flag=1
    with pytest.raises(ValueError): p.copy_reference(ref,mapping,flag)


def test_map_count_and_multisets(piece):
    raw,_=piece; trained=raw['training'][-1,2]
    for mapping in raw['copy_map']:
        assert np.count_nonzero(mapping!=np.arange(256))==64
        np.testing.assert_array_equal(mapping[mapping],np.arange(256))
    for state in raw['states'].reshape(-1,3,16,16):
        np.testing.assert_array_equal(np.sort(state[2],axis=None),np.sort(trained,axis=None))
        assert state[2].mean()==pytest.approx(trained.mean(),abs=1e-14)
        assert np.linalg.norm(state[2])==pytest.approx(np.linalg.norm(trained),abs=1e-14)


def test_between_copy_record_immutable(piece):
    raw,_=piece
    for ai in range(6):
        for c in range(1,SHORT.cycles+1):
            np.testing.assert_array_equal(raw['states'][ai,3*c-2,2],raw['states'][ai,3*c-1,2])
            np.testing.assert_array_equal(raw['states'][ai,3*c-2,2],raw['states'][ai,3*c,2])
    for ai in (0,3):
        for state in raw['states'][ai]: np.testing.assert_array_equal(state[2],raw['training'][-1,2])


def test_single_rescue_and_continued_damage(piece):
    raw,_=piece; stop=3*(SHORT.rescue_cycle-1)+1; initial=raw['training'][-1,2]
    np.testing.assert_array_equal(raw['states'][1,:stop],raw['states'][2,:stop])
    np.testing.assert_array_equal(raw['states'][1,stop,:2],raw['states'][2,stop,:2])
    np.testing.assert_array_equal(raw['states'][2,stop,2],initial)
    assert not np.array_equal(raw['pre_restore'][2,SHORT.rescue_cycle-1],initial)
    assert not np.array_equal(raw['states'][2,-1,2],initial)
    for c in (5,6):
        expected=p.copy_reference(raw['states'][2,3*(c-1),2],raw['copy_map'][c-1],True)
        np.testing.assert_array_equal(raw['states'][2,3*c,2],expected)


def test_reader_off_aliases(piece):
    raw,meta=piece
    for ai in (4,5):
        np.testing.assert_array_equal(raw['states'][ai,:,:2],raw['states'][3,:,:2])
        np.testing.assert_array_equal(raw['control'][ai],raw['control'][3])
        assert meta['branch_rng'][ai]==meta['branch_rng'][3]
    assert not np.array_equal(raw['states'][3,:,2],raw['states'][4,:,2])
    for ai in range(3): np.testing.assert_array_equal(raw['states'][ai,:,2],raw['states'][ai+3,:,2])


def test_target_exclusion(piece):
    raw,_=piece; ctx=p.context(p.DISPOSABLE)
    assert tuple(inspect.signature(p.balance).parameters)==('v',)
    assert 'ancestor' not in inspect.signature(p.branch).parameters and 'teacher' not in inspect.signature(p.branch).parameters
    class Poison:
        def __array__(self,*args,**kwargs): raise AssertionError('target accessed')
    for arm in ('clean_on','damaged_on','clean_off','damaged_off'):
        with pytest.raises(ValueError,match='forbidden'):
            p.branch(raw['training'][-1],raw['theta'],ctx,p.DISPOSABLE,0,arm,SHORT,backup=Poison())
    for arm in ('rescue_on','rescue_off'):
        with pytest.raises(ValueError,match='required'):
            p.branch(raw['training'][-1],raw['theta'],ctx,p.DISPOSABLE,0,arm,SHORT)


@pytest.mark.parametrize('arm',p.ARMS)
def test_branch_inputs_immutable(piece,arm):
    raw,_=piece; state=raw['training'][-1]; theta=raw['theta']; backup=state[2].copy()
    saved=[x.copy() for x in (state,theta,backup)]; ctx=p.context(p.DISPOSABLE)
    p.branch(state,theta,ctx,p.DISPOSABLE,0,arm,SHORT,backup=backup if 'rescue' in arm else None)
    for x,y in zip((state,theta,backup),saved): np.testing.assert_array_equal(x,y)
    assert ctx['bp'].rho==.002 and ctx['bp'].c_m==.2


def test_full_disposable_replay(block):
    raw,meta=block; assert p.checker().check_block(raw,meta,SHORT,replay=True)
    assert all(m['replay']['max_abs']==0 for m in meta['lives'])


def test_reverse_order_and_duplicate_aliases(piece):
    raw,meta=piece; order=p.ARMS[::-1]+('damaged_on',)
    other,om=p.simulate_life(p.DISPOSABLE,0,SHORT,arms=order)
    for ai,arm in enumerate(order):
        old=p.ARMS.index(arm)
        for key in ('states','control','pre_restore'): np.testing.assert_array_equal(other[key][ai],raw[key][old])
        for key in ('branch_rng','copy_rng'): assert om[key][ai]==meta[key][old]
    np.testing.assert_array_equal(other['copy_map'],raw['copy_map'])


def test_equal_noise_and_clocks(piece):
    raw,meta=piece; random=p.rng(p.DISPOSABLE,0,'branch:1')
    random.integers(0,2,1); random.integers(0,2,1)
    for _ in range(1+SHORT.teaching+SHORT.free): random.standard_normal((1,16,16))
    assert all(row[0]==canonical_digest(random.bit_generator.state) for row in meta['branch_rng'])
    errors=p.rng(p.DISPOSABLE,0,'copy:1'); errors.choice(256,64,replace=False)
    assert all(row[0]==canonical_digest(errors.bit_generator.state) for row in meta['copy_rng'])
    assert raw['control'].shape==(6,6,3,7) and np.max(abs(raw['control'][:,:,:,1]))<=1e-12


def test_d103_saved_baseline_anchor():
    p.api(); out=ROOT/'outputs'/p.base.RUN_ID
    raw=run.u.load_npz(out/'block_48000.npz'); meta=run.u.read_json(out/'block_48000.json')
    assert p.base.checker().check_block(raw,meta,p.base.CONFIG,replay=True)
    ctx=p.context(48000)
    for life in range(2):
        for arm,old_id in (('clean_on',1),('clean_off',4)):
            states,mask,digests,trace,*_=p.branch(raw['training'][life,-1],raw['theta'][life],ctx,48000,life,
                arm,tag=p.base.TAG)
            np.testing.assert_array_equal(states,raw['states'][life,old_id])
            np.testing.assert_array_equal(mask,raw['fresh'][life])
            np.testing.assert_array_equal(trace,raw['control'][life,old_id])
            assert digests==meta['lives'][life]['branch_rng'][old_id]


@pytest.mark.parametrize('field',['theta','ancestor','training','states','values','fresh','training_fresh','pre_restore'])
def test_state_corruption_rejected(piece,field):
    raw,meta=piece
    if raw[field].dtype==np.bool_: raw[field].flat[-1]=~raw[field].flat[-1]
    else: raw[field].flat[-1]+=.1
    with pytest.raises(AssertionError): p.checker().check_life(raw,meta,SHORT)


@pytest.mark.parametrize('defect',['clean_R','damage_R','restore_early','restore_again','copy_map',
    'pre_restore','off_V','off_EMA','off_trace'])
def test_copy_and_lesion_corruption_without_replay(piece,defect):
    raw,meta=piece
    if defect=='clean_R': raw['states'][0,4,2,0,0]+=.1
    elif defect=='damage_R': raw['states'][1,4,2]=raw['training'][-1,2]
    elif defect=='restore_early': raw['states'][2,1,2]=raw['training'][-1,2]
    elif defect=='restore_again': raw['states'][2,13,2]=raw['training'][-1,2]
    elif defect=='copy_map': raw['copy_map'][0]=raw['copy_map'][1]
    elif defect=='pre_restore': raw['pre_restore'][2,3]=raw['training'][-1,2]
    elif defect=='off_V': raw['states'][4,4,0,0,0]+=.1
    elif defect=='off_EMA': raw['states'][5,4,1,0,0]+=.1
    else: raw['control'][4,0,1,3]+=.1
    with pytest.raises(AssertionError): p.checker().check_life(raw,meta,SHORT,replay=False)


@pytest.mark.parametrize('column',range(7))
def test_controller_trace_corruption(piece,column):
    raw,meta=piece; raw['control'][1,0,0,column]+=.01
    with pytest.raises(AssertionError): p.checker().check_life(raw,meta,SHORT)


@pytest.mark.parametrize('field',['index','life','tag','config','arms','branch_rng','copy_rng',
    'founder_rng','theta_writable','arm_parameters'])
def test_metadata_corruption_rejected(piece,field):
    raw,meta=piece
    if field=='index': meta[field]+=1
    elif field=='life': meta[field]=True
    elif field=='config': meta[field]['teaching']+=1
    elif field=='arms': meta[field].reverse()
    elif field in ('branch_rng','copy_rng'): meta[field][0][0]='bad'
    elif field=='arm_parameters': meta[field][1][1]=.002
    else: meta[field]='bad'
    with pytest.raises(AssertionError): p.checker().check_life(raw,meta,SHORT)


def test_hand_built_primary(block):
    blocks=[deepcopy(block[0]) for _ in range(8)]
    for b in blocks:
        b['values'].fill(0); b['control'].fill(0); b['values'][:,:,3:,13]=64
        b['values'][:,0,3:,12]=48; b['values'][:,1,3:,12]=16
    summary=p.summarize(blocks,SHORT)
    assert summary['primary']['name']=='clean_on_minus_damaged_on' and summary['primary']['cycle']==6
    assert summary['primary']['mean']==.5 and summary['primary']['pointwise_block_bootstrap_95']==[.5,.5]
    assert summary['label']=='COPY_ADDRESS_DAMAGE_COST'


def test_independent_pooling(block):
    assert p.checker().check_summary(p.summarize([block[0]]*8,SHORT),[block[0]]*8,SHORT)


@pytest.mark.parametrize('field',['primary','label','rescue_contrast','record_diagnostics',
    'window_control_means','max_controlled_mean_residual','absolute_fidelity_gate'])
def test_summary_corruption_rejected(block,field):
    result=p.summarize([block[0]]*8,SHORT)
    if field in ('primary','rescue_contrast'): result[field]['mean']+=.01
    elif field=='label': result[field]='wrong'
    elif field=='record_diagnostics': result[field][0]['trained_mae']['mean']+=.1
    elif field=='window_control_means': result[field][1][0][0]+=.1
    elif field=='max_controlled_mean_residual': result[field]=.01
    else: result[field]=.8
    with pytest.raises(AssertionError): p.checker().check_summary(result,[block[0]]*8,SHORT)


@pytest.mark.parametrize('defect',['missing','nan','empty','unpaired','controller'])
def test_invalid_summary_input(block,defect):
    blocks=[deepcopy(block[0]) for _ in range(8)]
    if defect=='missing': blocks.pop()
    elif defect=='nan': blocks[0]['values'].flat[0]=np.nan
    elif defect=='empty': blocks[0]['values'][0,0,6,13]=0
    elif defect=='unpaired': blocks[0]['values'][0,0,6,13]+=1
    else: blocks[0]['control'][0,1,0,0,1]=.1
    with pytest.raises(ValueError): p.summarize(blocks,SHORT)


def test_saved_roundtrip_and_external_guard(block,tmp_path):
    raw,meta=block; loaded=run.u.save_pair(tmp_path,'block',raw,meta,ROOT)
    assert p.checker().check_block(loaded,run.u.read_json(tmp_path/'block.json'),SHORT,replay=False)
    with pytest.raises(FileExistsError): run.u.write_json(tmp_path/'block.json',{},ROOT)
    with pytest.raises(ValueError): run.u.write_npz(p.WS/'forbidden.npz',raw,ROOT)


def test_prior_run_not_monkeypatched():
    assert run.previous.p is p.base
    assert run.previous.contract()['decision']=='D103' and run.contract()['decision']=='D104'
    assert run.previous.contract()['fresh_branches']==112 and run.contract()['fresh_branches']==96


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
    result=subprocess.run([sys.executable,'-c','from laws_confirmation.l19_copy_damage import api; '
        'assert callable(api()["blueprint_step"])'],cwd=p.WS,env=os.environ.copy(),capture_output=True,text=True,timeout=30)
    assert result.returncode==0,result.stderr
