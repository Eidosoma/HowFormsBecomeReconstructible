"""D105 disposable mechanism checks and the known D104 baseline; no main draws."""
from copy import deepcopy
from dataclasses import replace
import inspect
import os
import subprocess
import sys

import numpy as np
import pytest

from laws_confirmation import l19_internal_repair as p
from laws_confirmation import l19_internal_repair_run as run
from laws_confirmation.io import DEFAULT_EXTERNAL_ROOT as ROOT,canonical_digest

SHORT=replace(p.CONFIG,settle=4,training_cycles=1,teaching=3,free=4)


@pytest.fixture(scope='module')
def block(): return p.execute_block(p.DISPOSABLE,SHORT)


@pytest.fixture
def piece(block):
    raw,meta=deepcopy(block)
    return {k:v[0] for k,v in raw.items()},meta['lives'][0]


def test_fixed_design():
    assert p.TISSUES==tuple(range(50000,50008)) and p.DISPOSABLE not in p.TISSUES
    assert p.CONFIG.primary_cycle==p.CONFIG.cycles==6 and p.CONFIG.damage_pairs==32
    assert len(p.ARMS)==8 and p.balance is p.base.balance
    assert p.contract()['reference_bytes']==2048 and p.contract()['backup_bytes']==0
    assert p.contract()['repair_persistent_extra_bytes']==0
    assert not p.contract()['repair_preserves_mean_rms_multiset']
    assert run.contract()['absolute_fidelity_gate'] is None
    assert p.contract()['fresh_branches']==128 and len(run.output_names())==19


@pytest.mark.parametrize('bad',[-1,True,1.5,'50000'])
def test_invalid_identity(bad):
    with pytest.raises(ValueError): p.context(bad)


@pytest.mark.parametrize('change',[dict(lives=0),dict(settle=-1),dict(cycles=2),dict(primary_cycle=2),
    dict(primary_cycle=7),dict(teaching=0),dict(free=0),dict(shift=16),dict(amplitude=float('nan')),
    dict(amp_threshold=2),dict(training_cycles=True),dict(damage_pairs=0),dict(damage_pairs=129),dict(damage_pairs=True)])
def test_config_validation(change):
    with pytest.raises(ValueError): replace(p.CONFIG,**change)


def test_hand_built_median_and_no_mutation():
    ref=np.arange(256,dtype=np.float64).reshape(16,16); saved=ref.copy()
    result=p.repair(ref)
    assert result[5,5]==85.
    assert result[0,0]==sorted([ref[y,x] for y in (15,0,1) for x in (15,0,1)])[4]
    np.testing.assert_array_equal(result,p.checker().median_pass(ref))
    np.testing.assert_array_equal(ref,saved); assert not np.shares_memory(ref,result)
    for value in (-1.3,0.,1.7):
        constant=np.full((16,16),value); np.testing.assert_array_equal(p.repair(constant),constant)


def test_repair_symmetries():
    ref=p.rng(p.DISPOSABLE,0,'unit-median').standard_normal((16,16)); result=p.repair(ref)
    np.testing.assert_array_equal(p.repair(-ref),-result)
    np.testing.assert_array_equal(p.repair(np.roll(ref,(5,7),(0,1))),np.roll(result,(5,7),(0,1)))
    np.testing.assert_array_equal(p.repair(np.rot90(ref)),np.rot90(result))
    np.testing.assert_array_equal(p.repair(ref.T),result.T)
    assert result.min()>=ref.min() and result.max()<=ref.max()


@pytest.mark.parametrize('defect',['wrong_shape','nan','inf','float32','list'])
def test_bad_repair_inputs(defect):
    ref=np.ones((16,16),dtype=np.float64)
    if defect=='wrong_shape': ref=ref.ravel()
    elif defect=='nan': ref[0,0]=np.nan
    elif defect=='inf': ref[0,0]=np.inf
    elif defect=='float32': ref=ref.astype(np.float32)
    else: ref=ref.tolist()
    with pytest.raises(ValueError): p.repair(ref)


def test_detail_observer_is_not_generic(piece):
    raw,_=piece; generic=np.full((16,16),-1.); generic[:,:8]=1.
    ancestor=generic.copy(); ancestor[3,2]=-1.
    np.testing.assert_array_equal(p.repair(ancestor),generic)  # repair can erase a genuine small feature
    states=raw['states'].copy(); states[:,::3,0]=generic
    content=p.content_measure(states,ancestor,raw['fresh'],p.ARMS,SHORT)
    assert np.all(content[0,:,4]==1) and np.all(content[0,:,5]==0)
    assert np.all(content[0,:,7]==1) and np.all(content[0,:,0]==255/256)
    states[0,::3,0]=ancestor
    content=p.content_measure(states,ancestor,raw['fresh'],p.ARMS,SHORT)
    assert np.all(content[0,:,5]==1) and np.all(content[0,:,0]==1)
    assert np.all(content[0,:,7]==255/256)


def test_detail_empty_policy(block):
    blocks=[deepcopy(block[0]) for _ in range(8)]
    for b in blocks: b['content'][:,:,:,4:7]=0
    result=p.summarize(blocks,SHORT)
    assert all(row['detail_body'] is None and row['detail_reference'] is None for row in result['trajectories'])
    assert result['blocks']==8 and result['lives_per_block']==2


def test_between_boundary_record_immutable(piece):
    raw,_=piece
    for ai in range(8):
        for c in range(1,SHORT.cycles+1):
            np.testing.assert_array_equal(raw['states'][ai,3*c-2,2],raw['states'][ai,3*c-1,2])
            np.testing.assert_array_equal(raw['states'][ai,3*c-2,2],raw['states'][ai,3*c,2])
    for state in raw['states'][0]: np.testing.assert_array_equal(state[2],raw['training'][-1,2])


def test_copy_then_local_repair(piece):
    raw,_=piece
    for ai,(_,gain,damaged,repaired,record) in enumerate(p.CASES):
        for c in range(1,SHORT.cycles+1):
            copied=p.base.copy_reference(raw['states'][ai,3*(c-1),2],raw['copy_map'][c-1],damaged)
            np.testing.assert_array_equal(copied,raw['pre_repair'][ai,c-1])
            expected=p.repair(copied) if repaired else copied
            np.testing.assert_array_equal(expected,raw['states'][ai,3*c-2,2])


def test_wrong_initial_content_and_common_body(piece):
    raw,_=piece; initial=raw['training'][-1]
    wrong=np.roll(initial[2],8,axis=-1)
    assert not np.array_equal(wrong,initial[2])
    for ai in range(8):
        np.testing.assert_array_equal(raw['states'][ai,0,:2],initial[:2])
        np.testing.assert_array_equal(raw['states'][ai,0,2],wrong if ai in (4,5) else initial[2])
    np.testing.assert_array_equal(np.sort(wrong,axis=None),np.sort(initial[2],axis=None))


def test_reader_off_aliases(piece):
    raw,meta=piece
    np.testing.assert_array_equal(raw['states'][6,:,:2],raw['states'][7,:,:2])
    np.testing.assert_array_equal(raw['control'][6],raw['control'][7])
    for a,b in ((1,6),(2,7)): np.testing.assert_array_equal(raw['states'][a,:,2],raw['states'][b,:,2])
    assert meta['branch_rng'][6]==meta['branch_rng'][7]
    assert not np.array_equal(raw['states'][6,:,2],raw['states'][7,:,2])


def test_target_exclusion(piece):
    raw,_=piece; ctx=p.context(p.DISPOSABLE)
    assert tuple(inspect.signature(p.repair).parameters)==('ref',)
    assert tuple(inspect.signature(p.balance).parameters)==('v',)
    assert not {'ancestor','teacher','backup','body'} & set(inspect.signature(p.branch).parameters)
    class Poison:
        def __array__(self,*args,**kwargs): raise AssertionError('target accessed')
    for arm in p.ARMS:
        for key in ('teacher','backup'):
            with pytest.raises(TypeError,match='unexpected keyword'):
                p.branch(raw['training'][-1],raw['theta'],ctx,p.DISPOSABLE,0,arm,SHORT,**{key:Poison()})


@pytest.mark.parametrize('arm',p.ARMS)
def test_branch_inputs_immutable(piece,arm):
    raw,_=piece; state=raw['training'][-1]; theta=raw['theta']; saved=[state.copy(),theta.copy()]
    ctx=p.context(p.DISPOSABLE); p.branch(state,theta,ctx,p.DISPOSABLE,0,arm,SHORT)
    for x,y in zip((state,theta),saved): np.testing.assert_array_equal(x,y)
    assert ctx['bp'].rho==.002 and ctx['bp'].c_m==.2


def test_full_disposable_replay(block):
    raw,meta=block; assert p.checker().check_block(raw,meta,SHORT,replay=True)
    assert all(m['replay']['max_abs']==0 for m in meta['lives'])


def test_reverse_order_and_duplicate_aliases(piece):
    raw,meta=piece; order=p.ARMS[::-1]+('repaired_on',)
    other,om=p.simulate_life(p.DISPOSABLE,0,SHORT,arms=order)
    for ai,arm in enumerate(order):
        old=p.ARMS.index(arm)
        for key in ('states','control','pre_repair','content'): np.testing.assert_array_equal(other[key][ai],raw[key][old])
        for key in ('branch_rng','copy_rng'): assert om[key][ai]==meta[key][old]


def test_equal_noise_and_clocks(piece):
    raw,meta=piece; random=p.rng(p.DISPOSABLE,0,'branch:1')
    random.integers(0,2,1); random.integers(0,2,1)
    for _ in range(1+SHORT.teaching+SHORT.free): random.standard_normal((1,16,16))
    assert all(row[0]==canonical_digest(random.bit_generator.state) for row in meta['branch_rng'])
    errors=p.rng(p.DISPOSABLE,0,'copy:1'); errors.choice(256,64,replace=False)
    assert all(row[0]==canonical_digest(errors.bit_generator.state) for row in meta['copy_rng'])
    assert raw['control'].shape==(8,6,3,7) and np.max(abs(raw['control'][:,:,:,1]))<=1e-12


def test_d104_saved_baseline_anchor():
    p.api(); out=ROOT/'outputs'/p.base.RUN_ID
    raw=run.u.load_npz(out/'block_49000.npz'); meta=run.u.read_json(out/'block_49000.json')
    assert p.base.checker().check_block(raw,meta,p.base.CONFIG,replay=True)
    ctx=p.context(49000)
    for life in range(2):
        for arm,old_id in (('clean_on',0),('damaged_on',1),('damaged_off',4)):
            states,mask,digests,trace,maps,errors,copied=p.branch(raw['training'][life,-1],raw['theta'][life],ctx,
                49000,life,arm,tag=p.base.TAG)
            for x,y in ((states,raw['states'][life,old_id]),(mask,raw['fresh'][life]),
                (trace,raw['control'][life,old_id]),(maps,raw['copy_map'][life]),(copied,raw['pre_restore'][life,old_id])):
                np.testing.assert_array_equal(x,y)
            assert digests==meta['lives'][life]['branch_rng'][old_id] and errors==meta['lives'][life]['copy_rng'][old_id]


@pytest.mark.parametrize('field',['theta','ancestor','training','states','values','fresh','training_fresh','pre_repair','content'])
def test_state_corruption_rejected(piece,field):
    raw,meta=piece
    if raw[field].dtype==np.bool_: raw[field].flat[-1]=~raw[field].flat[-1]
    else: raw[field].flat[-1]+=.1
    with pytest.raises(AssertionError): p.checker().check_life(raw,meta,SHORT)


@pytest.mark.parametrize('defect',['clean_R','repair_R','wrong_R','copy_map','pre_repair','off_V','off_EMA','off_trace'])
def test_intervention_corruption_without_replay(piece,defect):
    raw,meta=piece
    if defect=='clean_R': raw['states'][0,4,2,0,0]+=.1
    elif defect=='repair_R': raw['states'][2,4,2]=raw['pre_repair'][2,1]
    elif defect=='wrong_R': raw['states'][4,0,2]=raw['training'][-1,2]
    elif defect=='copy_map': raw['copy_map'][0]=raw['copy_map'][1]
    elif defect=='pre_repair': raw['pre_repair'][2,3]=raw['training'][-1,2]
    elif defect=='off_V': raw['states'][7,4,0,0,0]+=.1
    elif defect=='off_EMA': raw['states'][7,4,1,0,0]+=.1
    else: raw['control'][7,0,1,3]+=.1
    with pytest.raises(AssertionError): p.checker().check_life(raw,meta,SHORT,replay=False)


@pytest.mark.parametrize('column',range(7))
def test_controller_trace_corruption(piece,column):
    raw,meta=piece; raw['control'][2,0,0,column]+=.01
    with pytest.raises(AssertionError): p.checker().check_life(raw,meta,SHORT)


@pytest.mark.parametrize('column',range(9))
def test_content_observer_corruption(piece,column):
    raw,meta=piece; raw['content'][2,6,column]+=.01
    with pytest.raises(AssertionError): p.checker().check_life(raw,meta,SHORT,replay=False)


@pytest.mark.parametrize('field',['index','life','tag','config','arms','branch_rng','copy_rng','founder_rng','theta_writable','arm_parameters'])
def test_metadata_corruption_rejected(piece,field):
    raw,meta=piece
    if field=='index': meta[field]+=1
    elif field=='life': meta[field]=True
    elif field=='config': meta[field]['teaching']+=1
    elif field=='arms': meta[field].reverse()
    elif field in ('branch_rng','copy_rng'): meta[field][0][0]='bad'
    elif field=='arm_parameters': meta[field][2][1]=.002
    else: meta[field]='bad'
    with pytest.raises(AssertionError): p.checker().check_life(raw,meta,SHORT)


def test_hand_built_primary(block):
    blocks=[deepcopy(block[0]) for _ in range(8)]
    for b in blocks:
        b['values'].fill(0); b['control'].fill(0); b['content'].fill(0); b['values'][:,:,3:,13]=64
        b['content'][:,2,3:,1]=48; b['content'][:,1,3:,1]=16
        b['content'][:,3,3:,1]=8
    result=p.summarize(blocks,SHORT)
    assert result['primary']['name']=='repaired_minus_damaged' and result['primary']['mean']==.5
    assert result['primary']['pointwise_block_bootstrap_95']==[.5,.5]
    assert result['label']=='LOCAL_REPAIR_BODY_BENEFIT'
    assert result['contrasts'][2]['mean']==.375


def test_independent_pooling(block):
    assert p.checker().check_summary(p.summarize([block[0]]*8,SHORT),[block[0]]*8,SHORT)


@pytest.mark.parametrize('field',['primary','label','trajectories','content_means','window_control_means',
    'max_controlled_mean_residual','absolute_fidelity_gate','detail_missing_policy'])
def test_summary_corruption_rejected(block,field):
    result=p.summarize([block[0]]*8,SHORT)
    if field=='primary': result[field]['mean']+=.01
    elif field in ('label','detail_missing_policy'): result[field]='wrong'
    elif field=='trajectories': result[field][0]['incoming_R_mae']['mean']+=.1
    elif field in ('window_control_means','content_means'): result[field][1][0][0]+=.1
    elif field=='max_controlled_mean_residual': result[field]=.01
    else: result[field]=.8
    with pytest.raises(AssertionError): p.checker().check_summary(result,[block[0]]*8,SHORT)


@pytest.mark.parametrize('defect',['missing','nan','empty','unpaired','controller','nan_content'])
def test_invalid_summary_input(block,defect):
    blocks=[deepcopy(block[0]) for _ in range(8)]
    if defect=='missing': blocks.pop()
    elif defect=='nan': blocks[0]['values'].flat[0]=np.nan
    elif defect=='nan_content': blocks[0]['content'].flat[0]=np.nan
    elif defect=='empty': blocks[0]['values'][0,0,6,13]=0
    elif defect=='unpaired': blocks[0]['values'][0,0,6,13]+=1
    else: blocks[0]['control'][0,2,0,0,1]=.1
    with pytest.raises(ValueError): p.summarize(blocks,SHORT)


def test_saved_roundtrip_and_external_guard(block,tmp_path):
    raw,meta=block; loaded=run.u.save_pair(tmp_path,'block',raw,meta,ROOT)
    assert p.checker().check_block(loaded,run.u.read_json(tmp_path/'block.json'),SHORT,replay=False)
    with pytest.raises(FileExistsError): run.u.write_json(tmp_path/'block.json',{},ROOT)
    with pytest.raises(ValueError): run.u.write_npz(p.WS/'forbidden.npz',raw,ROOT)


def test_prior_run_not_monkeypatched():
    assert run.previous.p is p.base
    assert run.previous.contract()['decision']=='D104' and run.contract()['decision']=='D105'
    assert run.previous.contract()['fresh_branches']==96 and run.contract()['fresh_branches']==128


def test_missing_detachment_record_is_rejected(tmp_path):
    with pytest.raises(FileNotFoundError): run.detached_guard(tmp_path,True)


def test_reserved_run_is_not_reused(monkeypatch,tmp_path):
    monkeypatch.setattr(run.u,'preflight',lambda *a,**kw:None)
    monkeypatch.setattr(run,'main_inputs',lambda root:{})
    monkeypatch.setattr(run,'timing_checked',lambda root:{})
    (tmp_path/'runs'/p.RUN_ID).mkdir(parents=True)
    with pytest.raises(FileExistsError): run.prepare(tmp_path)


def test_fresh_process_import():
    result=subprocess.run([sys.executable,'-c','from laws_confirmation.l19_internal_repair import api; '
        'assert callable(api()["blueprint_step"])'],cwd=p.WS,env=os.environ.copy(),capture_output=True,text=True,timeout=30)
    assert result.returncode==0,result.stderr
