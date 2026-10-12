"""D106 disposable technical tests; no qualification or main-cohort draws."""
from copy import deepcopy
from dataclasses import replace
import inspect
import os
import subprocess
import sys

import numpy as np
import pytest

from laws_confirmation import l19_written_landmarks as p
from laws_confirmation import l19_written_landmarks_run as run
from laws_confirmation.io import DEFAULT_EXTERNAL_ROOT as ROOT,canonical_digest

SHORT=replace(p.CONFIG,settle=4,training_cycles=1,teaching=3,free=4)


@pytest.fixture(scope='module',params=[True,False],ids=['qualification','main'])
def block(request): return p.execute_block(p.DISPOSABLE,request.param,SHORT)


@pytest.fixture
def piece(block):
    raw,meta=deepcopy(block)
    return {k:v[0] for k,v in raw.items()},meta['lives'][0]


def test_d106_targets():
    taught,coarse,detail=p.targets(); other=p.checker().templates()
    for a,b in zip((taught,coarse,detail),other): np.testing.assert_array_equal(a,b)
    assert detail.sum()==16 and np.all((taught>0).sum(axis=(1,2))==128)
    assert np.all(np.sum(taught!=coarse,axis=(1,2))==8)
    assert np.all(taught[0,detail]==-taught[1,detail])
    np.testing.assert_array_equal(taught[1],np.roll(taught[0],8,axis=0))
    for record in taught: np.testing.assert_array_equal(p.repair(record),coarse)


def test_d106_fixed_design():
    assert p.TISSUES==tuple(range(51000,51008)) and p.QUAL_TISSUES==tuple(range(51500,51508))
    assert len(set(p.TISSUES+p.QUAL_TISSUES+(p.DISPOSABLE,)))==17
    assert p.CONFIG.cycles==p.CONFIG.primary_cycle==6 and p.CONFIG.damage_pairs==32
    assert p.repair is p.base.repair and p.balance is p.base.balance
    assert p.contract()['record_bytes']==2048 and p.contract()['backup_bytes']==0
    assert p.contract()['repair_persistent_extra_bytes']==0
    assert run.contract()['main_requires_qualified'] is True and run.contract()['absolute_fidelity_gate'] is None
    assert all(len(run.output_names(phase))==19 for phase in run.PHASES)
    assert run.previous.p is p.base and run.previous.contract()['decision']=='D105'


@pytest.mark.parametrize('bad',[-1,True,1.5,'51000'])
def test_d106_invalid_identity(bad):
    with pytest.raises(ValueError): p.context(bad)


@pytest.mark.parametrize('bad',[0,1,'qualification',None])
def test_d106_invalid_phase(bad):
    with pytest.raises(ValueError): p.arms_for(bad)


def test_d106_full_block_replay(block):
    raw,meta=block; assert p.checker().check_block(raw,meta,SHORT,replay=True)
    assert all(m['replay']['max_abs']==0 for m in meta['lives'])


def test_d106_native_writing_not_injection(piece):
    raw,meta=piece; targets=p.targets()[0]
    for k in range(2):
        assert not np.array_equal(raw['training'][k,-1,2],targets[k])
        assert not np.array_equal(raw['training'][k,-1,2],raw['founder'][2])
        np.testing.assert_array_equal(raw['training'][k,0],raw['founder'])
    assert meta['training_rng'][0]==meta['training_rng'][1]


def test_d106_common_untrained_recipient(piece):
    raw,meta=piece
    for k in range(2):
        for a in range(len(meta['arms'])):
            np.testing.assert_array_equal(raw['states'][k,a,0,:2],raw['founder'][:2])
            np.testing.assert_array_equal(raw['states'][k,a,0,2],raw['training'][k,-1,2])
    assert not np.array_equal(raw['training'][0,-1,:2],raw['training'][1,-1,:2])


def test_d106_wrong_content_identity(piece):
    raw,_=piece; values=p.measure(raw,SHORT)
    within=(values[0,:,:,0]-values[0,:,:,1]+values[1,:,:,0]-values[1,:,:,1])/2
    swapped=(values[0,:,:,0]-values[1,:,:,1]+values[1,:,:,0]-values[0,:,:,1])/2
    np.testing.assert_array_equal(within,swapped)
    taught,_,detail=p.targets(); final=raw['training'][:,-1,2]
    explicit=((final[0]-final[1])*taught[0])[detail].mean()
    assert explicit==pytest.approx(raw['training_values'][:,-1,0].sum(),abs=1e-15)


def test_d106_reader_off_aliases(piece):
    raw,meta=piece; ids=[a for a,arm in enumerate(meta['arms']) if arm.endswith('_off')]
    for k in range(2):
        for a in ids:
            np.testing.assert_array_equal(raw['states'][k,a,:,:2],raw['states'][0,ids[0],:,:2])
            np.testing.assert_array_equal(raw['control'][k,a],raw['control'][0,ids[0]])


def test_d106_target_exclusion(piece):
    raw,meta=piece
    assert tuple(inspect.signature(p.repair).parameters)==('ref',)
    assert tuple(inspect.signature(p.balance).parameters)==('v',)
    assert not {'teacher','backup','target','landmark','pattern'} & set(inspect.signature(p.branch).parameters)
    for key in ('teacher','backup','target','pattern'):
        with pytest.raises(TypeError,match='unexpected keyword'):
            p.branch(raw['states'][0,0,0],raw['theta'],p.context(p.DISPOSABLE),p.DISPOSABLE,0,
                meta['arms'][0],SHORT,**{key:object()})


def test_d106_order_alias_and_immutable_inputs(piece):
    raw,meta=piece; initial=raw['states'][0,0,0].copy(); theta=raw['theta']; before=initial.copy(); ctx=p.context(p.DISPOSABLE)
    for a in reversed(range(len(meta['arms']))):
        outcome=p.branch(initial,theta,ctx,p.DISPOSABLE,0,meta['arms'][a],SHORT)
        for pos,key in ((0,'states'),(3,'control'),(6,'pre_repair')): np.testing.assert_array_equal(outcome[pos],raw[key][0,a])
    np.testing.assert_array_equal(initial,before)
    assert ctx['bp'].rho==.002 and ctx['bp'].c_m==.2


def test_d106_equal_noise_and_clocks(piece):
    raw,meta=piece; random=p.rng(p.DISPOSABLE,0,'branch:1')
    random.integers(0,2,1); random.integers(0,2,1)
    for _ in range(1+SHORT.teaching+SHORT.free): random.standard_normal((1,16,16))
    assert all(row[0]==canonical_digest(random.bit_generator.state) for pattern in meta['branch_rng'] for row in pattern)
    assert np.max(abs(raw['control'][...,1]))<=1e-12


def test_d105_saved_baseline_anchor():
    p.api(); out=ROOT/'outputs'/p.base.RUN_ID
    raw=run.io.load_npz(out/'block_50000.npz'); meta=run.io.read_json(out/'block_50000.json')
    assert p.base.checker().check_block(raw,meta,p.base.CONFIG,replay=True)
    for life in range(2):
        for arm in p.MAIN_ARMS:
            ai=p.base.ARMS.index(arm)
            outcome=p.branch(raw['training'][life,-1],raw['theta'][life],p.context(50000),50000,life,arm,tag=p.base.TAG)
            for pos,key in ((0,'states'),(3,'control'),(6,'pre_repair')):
                np.testing.assert_array_equal(outcome[pos],raw[key][life,ai])
            np.testing.assert_array_equal(outcome[1],raw['fresh'][life]); np.testing.assert_array_equal(outcome[4],raw['copy_map'][life])
            assert outcome[2]==meta['lives'][life]['branch_rng'][ai] and outcome[5]==meta['lives'][life]['copy_rng'][ai]


@pytest.mark.parametrize('field',['theta','founder','training','training_fresh','states','fresh','copy_map','pre_repair','values','training_values'])
def test_d106_raw_corruption(piece,field):
    raw,meta=piece
    if raw[field].dtype==np.bool_: raw[field].flat[-1]=~raw[field].flat[-1]
    elif raw[field].dtype==np.int64: raw[field].flat[-1]=999
    else: raw[field].flat[-1]+=.1
    with pytest.raises(AssertionError): p.checker().check_life(raw,meta,SHORT)


@pytest.mark.parametrize('column',range(12))
def test_d106_observer_corruption(piece,column):
    raw,meta=piece; raw['values'][0,0,6,column]+=.1
    with pytest.raises(AssertionError): p.checker().check_life(raw,meta,SHORT,replay=False)


@pytest.mark.parametrize('column',range(7))
def test_d106_trace_corruption(piece,column):
    raw,meta=piece; raw['control'][0,0,0,0,column]+=.1
    with pytest.raises(AssertionError): p.checker().check_life(raw,meta,SHORT)


@pytest.mark.parametrize('field',['index','life','qualification','config','arms','tag','branch_rng','copy_rng','training_rng','founder_rng','theta_writable','arm_parameters'])
def test_d106_metadata_corruption(piece,field):
    raw,meta=piece
    if field=='index': meta[field]+=1
    elif field=='life': meta[field]=True
    elif field=='qualification': meta[field]=not meta[field]
    elif field=='config': meta[field]['teaching']+=1
    elif field=='arms': meta[field].reverse()
    elif field in ('branch_rng','copy_rng'): meta[field][0][0][0]='bad'
    elif field=='training_rng': meta[field][0][0]='bad'
    elif field=='arm_parameters': meta[field][0][1]=0.
    else: meta[field]='bad'
    with pytest.raises(AssertionError): p.checker().check_life(raw,meta,SHORT)


def test_d106_independent_pooling(block):
    raw,meta=block; result=p.summarize([raw]*8,meta['qualification'],SHORT)
    assert p.checker().check_summary(result,[raw]*8,meta['qualification'],SHORT)


def synthetic(qualification):
    n=len(p.arms_for(qualification))
    return [dict(values=np.zeros((2,2,n,7,12)),control=np.zeros((2,2,n,6,3,7)),
        training_values=np.full((2,2,4,4),.1)) for _ in range(8)]


def test_d106_hand_built_pooling():
    blocks=synthetic(False)
    for i,b in enumerate(blocks):
        b['values'][:,:,2,:,0]=.75; b['values'][:,:,2,:,1]=.25
        b['values'][:,:,1,:,0]=b['values'][:,:,1,:,1]=.5
    result=p.summarize(blocks,False,SHORT)
    assert result['primary']['mean']==.5 and result['primary']['pointwise_block_bootstrap_95']==[.5,.5]
    assert result['primary']['observer']=='landmark_specificity' and result['primary']['cycle']==6
    for i,b in enumerate(blocks): b['values'][:,:,2,:,0]=i/8
    result=p.summarize(blocks,False,SHORT)
    assert result['primary']['block_means']==[i/8-.25 for i in range(8)]
    assert result['primary']['mean']==.1875 and result['blocks']==8


def test_d106_qualification_gates():
    blocks=synthetic(True)
    for b in blocks:
        b['values'][:,:,0,:,0]=.75; b['values'][:,:,0,:,1]=.25; b['values'][:,:,1,:,0]=.5
    result=p.summarize(blocks,True,SHORT)
    assert result['qualified'] is True and [g['mean'] for g in result['gates']]==[.2,.5,.25]
    for gate in range(3):
        changed=deepcopy(blocks)
        for b in changed:
            if gate==0: b['training_values'].fill(0)
            elif gate==1: b['values'][:,:,0,:,1]=.75
            else: b['values'][:,:,1,:,0]=.75
        assert p.summarize(changed,True,SHORT)['qualified'] is False


@pytest.mark.parametrize('field',['primary','qualified','label','cell_means','training_means','training_projection_trajectory','landmark_cells','absolute_fidelity_gate'])
def test_d106_summary_corruptions(block,field):
    raw,meta=block; result=p.summarize([raw]*8,meta['qualification'],SHORT)
    if field=='primary': result[field]['mean']+=.1
    elif field=='cell_means': result[field][0][0][0][0]+=.1
    elif field=='training_means': result[field][0][0][0]+=.1
    elif field=='training_projection_trajectory': result[field][0]['mean']+=.1
    elif field=='qualified': result[field]=not result[field]
    elif field=='landmark_cells': result[field]=256
    elif field=='absolute_fidelity_gate': result[field]=.8
    else: result[field]='bad'
    with pytest.raises(AssertionError): p.checker().check_summary(result,[raw]*8,meta['qualification'],SHORT)


def test_d106_failed_qualification_blocks_main(monkeypatch,tmp_path):
    monkeypatch.setattr(run,'audit',lambda *a,**kw:dict(passes=True))
    monkeypatch.setattr(run.io,'read_json',lambda *a,**kw:dict(qualification=True,qualified=False))
    with pytest.raises(RuntimeError,match='qualification failed'): run.qualification_artifacts(tmp_path)
    assert not (tmp_path/'runs'/p.RUN_ID).exists()
    for bad in ({},dict(qualification=False,qualified=True),dict(qualification=True,qualified=1)):
        with pytest.raises(RuntimeError): run.require_qualified(bad)


def test_d106_saved_roundtrip_and_external_guard(block,tmp_path):
    raw,meta=block; saved=run.io.save_pair(tmp_path,'block',raw,meta,ROOT)
    assert p.checker().check_block(saved,run.io.read_json(tmp_path/'block.json'),SHORT,replay=False)
    with pytest.raises(FileExistsError): run.io.write_json(tmp_path/'block.json',{},ROOT)
    with pytest.raises(ValueError): run.io.write_npz(p.WS/'forbidden.npz',raw,ROOT)


def test_d106_missing_detachment_record_is_rejected(tmp_path):
    with pytest.raises(FileNotFoundError): run.detached_guard(tmp_path,'main',True)


def test_d106_reserved_run_is_not_reused(monkeypatch,tmp_path):
    monkeypatch.setattr(run.io,'preflight',lambda *a,**kw:None)
    monkeypatch.setattr(run,'input_hashes',lambda *a:{})
    monkeypatch.setattr(run,'timing_checked',lambda *a:{})
    (tmp_path/'runs'/p.RUN_ID).mkdir(parents=True)
    with pytest.raises(FileExistsError): run.prepare(tmp_path,'main')


def test_d106_fresh_process_import():
    result=subprocess.run([sys.executable,'-c','from laws_confirmation.l19_written_landmarks import api; '
        'assert callable(api()["blueprint_step"])'],cwd=p.WS,env=os.environ.copy(),capture_output=True,text=True,timeout=30)
    assert result.returncode==0,result.stderr
