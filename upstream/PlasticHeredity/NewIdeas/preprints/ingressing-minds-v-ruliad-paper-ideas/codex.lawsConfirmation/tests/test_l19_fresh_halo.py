"""D109 tests: disposable fresh parents/readers, plus retained D106/D108 bridges only."""
from copy import deepcopy
from dataclasses import replace
import inspect
import os
import subprocess
import sys

import numpy as np
import pytest

from laws_confirmation import l19_fresh_halo as p
from laws_confirmation import l19_fresh_halo_run as run
from laws_confirmation.io import DEFAULT_EXTERNAL_ROOT as ROOT,canonical_digest

SHORT=replace(p.CONFIG,settle=4,teaching=3,free=4)
SHORT_PARENT=replace(p.PARENT_CONFIG,settle=4,training_cycles=1,teaching=3,free=4)


@pytest.fixture(scope='module')
def block(): return p.execute_block(p.DISPOSABLE,SHORT,SHORT_PARENT)


@pytest.fixture
def piece(block):
    raw,meta=deepcopy(block)
    return {k:v[0] for k,v in raw.items()},meta['lives'][0]


def test_d109_fixed_contract():
    c=run.contract()
    assert p.TISSUES==tuple(range(55000,55008)) and p.SOURCE_TISSUES==tuple(range(54000,54008))
    assert c['R_bytes']==2048 and c['backup_bytes']==c['extra_persistent_bytes']==0
    assert c['post_mix_repair_or_damage'] is False and c['record_normalisation'] is False
    assert c['fresh_branches']==704 and c['exact_alias_branches']==48
    assert c['independent_life_replays']==32 and c['absolute_fidelity_gate'] is None
    assert p.CONFIG.cycles==1 and p.CONFIG.teaching==500 and p.CONFIG.free==1000
    assert run.previous.p is p.base and len(run.output_names())==19


@pytest.mark.parametrize('index',p.TISSUES+(p.DISPOSABLE,))
def test_d109_source_identity(index):
    expected=514209 if index==514210 else index-1000
    assert p.source_index(index)==expected
    assert p.source_proof(index)['source_index']==expected


@pytest.mark.parametrize('bad',[-1,0,True,55000.,'55000',54000,55008,None])
def test_d109_invalid_identity(bad):
    with pytest.raises(ValueError): p.context(bad)


@pytest.mark.parametrize('key,value',[(k,v) for k in ('lives','settle','teaching','free') for v in (0,True,1.5)]+
    [('cycles',2),('cycles',True),('lives',1),('damage_pairs',31),('damage_pairs',True),
     ('amp_threshold',0),('amp_threshold',2),('amp_threshold',float('nan')),('amp_threshold',True)])
def test_d109_invalid_config(key,value):
    with pytest.raises(ValueError): replace(p.CONFIG,**{key:value})


@pytest.mark.parametrize('landmark,near,far',p.FACTORS)
def test_d109_mosaic_identity(landmark,near,far):
    refs=np.arange(512,dtype=np.float64).reshape(2,16,16); before=refs.copy()
    result=p.mix(refs,landmark,near,far); detail,ring,outer=p.regions()
    assert detail.sum()==16 and (~detail).sum()==240 and result.nbytes==2048
    np.testing.assert_array_equal(result[detail],refs[landmark,detail])
    np.testing.assert_array_equal(result[ring],refs[near,ring])
    np.testing.assert_array_equal(result[outer],refs[far,outer])
    np.testing.assert_array_equal(refs,before)
    assert not np.shares_memory(result,refs)
    if landmark==near==far: np.testing.assert_array_equal(result,refs[landmark])


@pytest.mark.parametrize('axis',range(3))
@pytest.mark.parametrize('bad',[-1,2,True,0.,'1'])
def test_d109_invalid_selectors(axis,bad):
    selectors=[0,0,0]; selectors[axis]=bad
    with pytest.raises(ValueError): p.mix(np.zeros((2,16,16)),*selectors)


@pytest.mark.parametrize('bad',[None,[],np.zeros((16,16)),np.zeros((2,16,16),dtype=np.float32),
    np.full((2,16,16),np.nan),np.full((2,16,16),np.inf)])
def test_d109_invalid_records(bad):
    with pytest.raises(ValueError): p.mix(bad,0,1,0)


def test_d109_full_disposable_replay(block):
    raw,meta=block
    assert p.checker().check_block(raw,meta,SHORT,replay=True,parent_cfg=SHORT_PARENT)
    assert all(m['replay']['max_abs']==0 and m['exact_alias_branches']==2 for m in meta['lives'])


def test_d109_source_transfers(piece):
    raw,meta=piece
    refs=np.stack([raw['parent_states'][:,a,3*SHORT_PARENT.cycles,2] for a in (0,2)])
    np.testing.assert_array_equal(raw['source_R'],refs); assert meta['source']==p.source_proof(p.DISPOSABLE,SHORT_PARENT)
    for h in range(2):
        for m in range(8):
            for r in range(2):
                np.testing.assert_array_equal(raw['states'][h,m,r,0,:2],raw['recipient'][:2])
                np.testing.assert_array_equal(raw['states'][h,m,r,:,2],np.broadcast_to(raw['mosaics'][h,m],(4,16,16)))
                np.testing.assert_array_equal(raw['pre_repair'][h,m,r,0],raw['mosaics'][h,m])


def test_d109_fresh_records_and_fresh_recipient(piece):
    raw,meta=piece; source=meta['source']
    assert source['known_source_outcomes'] is False and source['source_cycle']==6
    assert source['fresh_physical_tissue_parameters'] is True
    for h,a in enumerate((0,2)):
        np.testing.assert_array_equal(raw['source_R'][h],raw['parent_states'][:,a,18,2])
        assert not np.array_equal(raw['recipient'][:2],raw['parent_states'][0,a,18,:2])
    np.testing.assert_array_equal(raw['theta'],raw['parent_theta'])
    assert not np.array_equal(raw['recipient'][:2],raw['parent_founder'][:2])
    assert p.rng(p.DISPOSABLE,0,'recipient').bit_generator.state!=p.writer.rng(p.DISPOSABLE_SOURCE,0,'founder').bit_generator.state
    assert meta['parent']['index']==p.DISPOSABLE_SOURCE and meta['parent']['qualification'] is False
    assert tuple(meta['parent']['arms'])==p.writer.MAIN_ARMS
    assert meta['replay']['parent_replay']['full_life_replay'] is True
    assert meta['parent']['exact_alias_branches']==1 and meta['exact_alias_branches']==2


def test_d109_off_aliases(piece):
    raw,_=piece
    for h in range(2):
        for m in range(8):
            np.testing.assert_array_equal(raw['states'][h,m,1,:,:2],raw['states'][0,0,1,:,:2])
            np.testing.assert_array_equal(raw['control'][h,m,1],raw['control'][0,0,1])


def test_d109_target_exclusion(piece):
    raw,_=piece; forbidden=('teacher','target','backup','history','mask','pattern','landmark')
    assert not set(forbidden)&set(inspect.signature(p.read).parameters)
    for key in forbidden:
        with pytest.raises(TypeError,match='unexpected keyword'):
            p.read(raw['mosaics'][0,0],raw['recipient'],raw['theta'],p.context(p.DISPOSABLE),
                p.DISPOSABLE,0,'on',SHORT,**{key:object()})


def test_d109_equal_noise_and_clocks(piece):
    raw,meta=piece; random=p.rng(p.DISPOSABLE,0,'branch:1')
    random.integers(0,2,1); random.integers(0,2,1)
    for _ in range(1+SHORT.teaching+SHORT.free): random.standard_normal((1,16,16))
    digest=canonical_digest(random.bit_generator.state)
    assert all(r==[digest] for h in meta['branch_rng'] for m in h for r in m)
    assert all(r==meta['copy_rng'][0][0][0] for h in meta['copy_rng'] for m in h for r in m)
    assert np.max(abs(raw['control'][...,1]))<=1e-12


def test_d109_order_alias_and_no_mutation(piece):
    raw,meta=piece; recipient=raw['recipient'].copy(); records=raw['mosaics'].copy(); theta=raw['theta'].copy()
    ctx=p.context(p.DISPOSABLE)
    for h in (1,0):
        for m in reversed(range(8)):
            for r in (1,0):
                result=p.read(records[h,m],recipient,theta,ctx,p.DISPOSABLE,0,p.READERS[r],SHORT)
                for pos,key in ((0,'states'),(3,'control'),(6,'pre_repair')):
                    np.testing.assert_array_equal(result[pos],raw[key][h,m,r])
    for a,b in ((recipient,raw['recipient']),(records,raw['mosaics']),(theta,raw['theta'])):
        np.testing.assert_array_equal(a,b)
    assert ctx['bp'].rho==.002 and ctx['bp'].c_m==.2


def test_d106_saved_parent_anchor():
    directory=ROOT/'tmp'/'l19_written_landmarks_v1_attempt1_benchmark'
    saved=run.u.load_npz(directory/'main.npz'); meta=run.u.read_json(directory/'main.json')
    for life in range(2):
        raw,record=p.writer.simulate_life(514206,life,False,p.PARENT_CONFIG)
        assert set(raw)==set(saved)
        for key in raw: np.testing.assert_array_equal(raw[key],saved[key][life])
        expected={k:v for k,v in meta['lives'][life].items() if k not in ('replay','exact_alias_branches')}
        p.checker().nested(record,expected)


def test_d108_saved_reader_anchor():
    p.api(); directory=ROOT/'tmp'/f'{p.base.RUN_ID}_benchmark'
    saved=run.u.load_npz(directory/'block_514208.npz'); meta=run.u.read_json(directory/'block_514208.json')
    assert p.base.checker().check_block(saved,meta,p.base.CONFIG,replay=True)
    for life in range(2):
        raw,record=p.simulate_reader(514208,life,saved['source_R'][life],meta['lives'][life]['source'],
            ctx=p.base.context(514208),tag=p.base.TAG)
        assert set(raw)==set(saved)
        for key in raw: np.testing.assert_array_equal(raw[key],saved[key][life])
        expected={k:v for k,v in meta['lives'][life].items() if k not in ('replay','exact_alias_branches')}
        p.checker().nested(record,expected)


@pytest.mark.parametrize('field',['regions','theta','recipient','source_R','mosaics','states','fresh','copy_map','pre_repair','values'])
def test_d109_raw_corruption(piece,field):
    raw,meta=piece
    if raw[field].dtype==np.bool_: raw[field].flat[-1]=~raw[field].flat[-1]
    elif raw[field].dtype==np.int64: raw[field].flat[-1]=999
    else: raw[field].flat[-1]+=.1
    with pytest.raises(AssertionError): p.checker().check_life(raw,meta,SHORT,SHORT_PARENT)


@pytest.mark.parametrize('column',range(10))
def test_d109_observer_corruption(piece,column):
    raw,meta=piece; raw['values'][0,0,0,3,column]+=.1
    with pytest.raises(AssertionError): p.checker().check_life(raw,meta,SHORT,SHORT_PARENT,replay=False)


@pytest.mark.parametrize('column',range(7))
def test_d109_trace_corruption(piece,column):
    raw,meta=piece; raw['control'][0,0,0,0,0,column]+=.1
    with pytest.raises(AssertionError): p.checker().check_life(raw,meta,SHORT,SHORT_PARENT)


@pytest.mark.parametrize('field',['index','life','config','tag','histories','mosaics','readers','phases','factors',
    'recipient_rng','branch_rng','copy_rng','theta_writable','region_names','region_sizes','partition'])
def test_d109_metadata_corruption(piece,field):
    raw,meta=piece
    if field=='index': meta[field]=55008
    elif field=='life': meta[field]=True
    elif field=='config': meta[field]['teaching']+=1
    elif field in ('histories','mosaics','readers','phases','factors','region_names','region_sizes'): meta[field].reverse()
    elif field in ('branch_rng','copy_rng'): meta[field][0][0][0][0]='bad'
    else: meta[field]='bad'
    with pytest.raises(AssertionError): p.checker().check_life(raw,meta,SHORT,SHORT_PARENT)


@pytest.mark.parametrize('field',['source_index','source_run','source_cycle','source_arms','source_seed_tag','source_storage','known_source_outcomes','fresh_physical_tissue_parameters'])
def test_d109_source_metadata_corruption(piece,field):
    raw,meta=piece; meta['source'][field]='bad'
    with pytest.raises(AssertionError): p.checker().check_life(raw,meta,SHORT,SHORT_PARENT,replay=False)


def test_d109_independent_pooling(block):
    raw,_=block; result=p.summarize([raw]*8,SHORT)
    assert p.checker().check_summary(result,[raw]*8,SHORT)
    assert len(result['contrasts'])==288 and len(result['trajectories'])==128


def synthetic(y=(1,1,-1,-1,1,1,-1,-1)):
    blocks=[dict(values=np.zeros((2,2,8,2,4,10)),control=np.zeros((2,2,8,2,1,3,7))) for _ in range(8)]
    for b in blocks:
        for m in range(8): b['values'][:,:,m,0,:,2]=y[m]
    return blocks


@pytest.mark.parametrize('y',[(1,1,-1,-1,1,1,-1,-1),(1,-1,1,-1,1,-1,1,-1),
    (1,-1,-1,1,-1,1,1,-1),(.8,.3,-.7,-.2,.5,.1,-.3,-.9),(0,)*8])
def test_d109_coefficient_algebra(y):
    effect={name:float(np.dot(coefs,y)) for name,coefs in p.CONTRASTS}
    assert effect['near_main']+effect['far_main']==pytest.approx(effect['coupled_outside_contribution'])
    assert effect['near_main']-effect['far_main']==pytest.approx(effect['near_minus_far'])
    assert effect['landmark_main']+effect['three_way_interaction']==pytest.approx(effect['coupled_landmark_contribution'])
    assert sum(effect[n] for n in ('landmark_main','near_main','far_main','three_way_interaction'))==pytest.approx(effect['full_record_identity'])
    for region in p.REGIONS:
        assert np.mean([v for k,v in effect.items() if k.startswith(region+'_at_')])==pytest.approx(effect[region+'_main'])
    result=p.summarize(synthetic(y),SHORT)
    for row in result['contrasts']: assert row['mean']==pytest.approx(0 if row['reader']=='off' else effect[row['name']])


@pytest.mark.parametrize('y,label',[
    ((1,1,-1,-1,1,1,-1,-1),'NEAR_HALO_DOMINATES'),
    ((1,-1,1,-1,1,-1,1,-1),'DISTANT_REGION_DOMINATES'),
    ((1,0,0,-1,1,0,0,-1),'NEAR_FAR_ATTRIBUTION_UNRESOLVED'),
    ((0,1,-1,0,0,1,-1,0),'REPAIRED_RECORD_READ_NOT_QUALIFIED'),
    ((0,)*8,'REPAIRED_RECORD_READ_NOT_QUALIFIED'),
    ((1,1,1,1,-1,-1,-1,-1),'REPAIRED_OUTSIDE_SIGNAL_NOT_QUALIFIED'),
    ((.5,1,0,.5,-.5,0,-1,-.5),'REPAIRED_OUTSIDE_SIGNAL_NOT_QUALIFIED')])
def test_d109_gate_no_localisation(y,label):
    result=p.summarize(synthetic(y),SHORT); assert result['label']==label
    if label.endswith('NOT_QUALIFIED'): assert result['readability'][1]['qualified'] is False


def test_d109_eight_source_blocks_not_conditions():
    blocks=synthetic()
    for i,b in enumerate(blocks):
        b['values'][:,1,:,:,3,2]=0
        b['values'][0,1,1,0,3,2]=i/8; b['values'][1,1,1,0,3,2]=(i+1)/8
    result=p.summarize(blocks,SHORT)
    expected=[(2*i+1)/64 for i in range(8)]
    assert result['primary']['block_means']==expected and result['blocks']==8
    assert result['primary']['mean']==np.mean(expected)
    assert np.asarray(result['primary']['life_values']).shape==(8,2)


def test_d109_label_reversal_invariance():
    y=np.array([.8,.3,-.7,-.2,.5,.1,-.3,-.9]); reversed_y=-y[::-1]
    for name,coefs in p.CONTRASTS[:12]:
        sign=-1 if name in ('landmark_near_interaction','landmark_far_interaction','near_far_interaction') else 1
        assert np.dot(coefs,reversed_y)==pytest.approx(sign*np.dot(coefs,y))


def test_d109_partition():
    actual=p.regions(); np.testing.assert_array_equal(actual,p.checker().masks_expected())
    assert actual.shape==(3,16,16) and actual.dtype==np.bool_
    np.testing.assert_array_equal(actual.sum((1,2)),[16,48,192])
    assert np.all(actual.sum(0)==1)
    detail=np.argwhere(actual[0])
    for y in range(16):
        for x in range(16):
            diff=np.abs(detail-np.array([y,x])); dist=np.min(np.max(np.minimum(diff,16-diff),axis=1))
            assert actual[0,y,x]==(dist==0) and actual[1,y,x]==(dist==1) and actual[2,y,x]==(dist>=2)
    assert p.CONFIG is p.base.CONFIG and p.measure is p.base.measure


def test_d109_three_way_identity():
    y=np.array([1,-1,-1,1,-1,1,1,-1])
    effect={name:float(np.dot(coefs,y)) for name,coefs in p.CONTRASTS}
    assert effect['full_record_identity']==effect['three_way_interaction']==1
    assert sum(effect[n] for n in ('landmark_main','near_main','far_main'))==0
    assert effect['coupled_landmark_contribution']==1 and effect['coupled_outside_contribution']==0
    assert p.CONTRASTS==p.checker().CONTRASTS


@pytest.mark.parametrize('inside,outside',p.base.base.FACTORS)
def test_d109_coupled_d107_subset(inside,outside):
    refs=np.arange(512,dtype=np.float64).reshape(2,16,16)
    np.testing.assert_array_equal(p.mix(refs,inside,outside,outside),p.base.base.mix(refs,inside,outside))
    assert p.FACTORS.index((inside,outside,outside)) in (0,3,4,7)


@pytest.mark.parametrize('field',['primary','readability','label','contrasts','trajectories','cell_means',
    'landmark_cells','near_cells','far_cells','absolute_fidelity_gate','source_records_previously_observed','fresh_physical_tissue_parameters'])
def test_d109_summary_corruption(block,field):
    raw,_=block; result=p.summarize([raw]*8,SHORT)
    if field=='primary': result[field]['mean']+=.1
    elif field=='readability': result[field][1]['qualified']=not result[field][1]['qualified']
    elif field=='contrasts': result[field][0]['mean']+=.1
    elif field=='trajectories': result[field][0]['A_detail']['mean']+=.1
    elif field=='cell_means': result[field][0][0][0][0][0]+=.1
    elif field in ('landmark_cells','near_cells','far_cells'): result[field]=256
    elif field=='absolute_fidelity_gate': result[field]=.8
    elif field in ('source_records_previously_observed','fresh_physical_tissue_parameters'): result[field]=not result[field]
    else: result[field]='bad'
    with pytest.raises(AssertionError): p.checker().check_summary(result,[raw]*8,SHORT)


def test_d109_saved_roundtrip_and_external_guard(block,tmp_path):
    raw,meta=block; saved=run.u.save_pair(tmp_path,'block',raw,meta,ROOT)
    assert p.checker().check_block(saved,run.u.read_json(tmp_path/'block.json'),SHORT,replay=False,parent_cfg=SHORT_PARENT)
    with pytest.raises(FileExistsError): run.u.write_json(tmp_path/'block.json',{},ROOT)
    with pytest.raises(ValueError): run.u.write_npz(p.WS/'forbidden.npz',raw,ROOT)


def test_d109_missing_detachment_record_is_rejected(tmp_path):
    with pytest.raises(FileNotFoundError): run.detached_guard(tmp_path,True)


def test_d109_reserved_run_is_not_reused(monkeypatch,tmp_path):
    monkeypatch.setattr(run.u,'preflight',lambda *a,**kw:None)
    monkeypatch.setattr(run,'main_inputs',lambda *a:{})
    monkeypatch.setattr(run,'timing_checked',lambda *a:{})
    (tmp_path/'runs'/p.RUN_ID).mkdir(parents=True)
    with pytest.raises(FileExistsError): run.prepare(tmp_path)


def test_d109_fresh_process_import():
    result=subprocess.run([sys.executable,'-c','from laws_confirmation.l19_fresh_halo import api; '
        'assert callable(api()["blueprint_step"])'],cwd=p.WS,env=os.environ.copy(),capture_output=True,text=True,timeout=30)
    assert result.returncode==0,result.stderr


def test_d109_unchanged_native_rulebook():
    assert p.PARENT_CONFIG is p.writer.CONFIG and p.CONFIG is p.base.CONFIG
    assert p.regions is p.base.regions and p.mix is p.base.mix and p.measure is p.base.measure
    assert p.CONTRASTS==p.base.CONTRASTS==p.checker().CONTRASTS
    assert p.PARENT_CONFIG.training_cycles==3 and p.PARENT_CONFIG.cycles==6
    assert p.PARENT_CONFIG.teaching==500 and p.PARENT_CONFIG.free==1000
    assert p.PARENT_CONFIG.damage_pairs==32 and p.PARENT_CONFIG.amp_threshold==.2


def test_d109_no_retained_source_loader(monkeypatch):
    def forbidden(*a,**kw): raise AssertionError('retained source loader invoked')
    monkeypatch.setattr(p.base,'load_source',forbidden)
    monkeypatch.setattr(p.base.base,'load_source',forbidden)
    raw,meta=p.simulate_life(p.DISPOSABLE,0,SHORT,SHORT_PARENT)
    assert 'parent_training' in raw and meta['source']['known_source_outcomes'] is False
    assert 'load_source' not in inspect.getsource(p.simulate_life)


@pytest.mark.parametrize('field',['theta','founder','training','training_fresh','states','fresh','control',
    'copy_map','pre_repair','values','training_values'])
def test_d109_parent_raw_corruption(piece,field):
    raw,meta=piece; value=raw['parent_'+field]
    if value.dtype==np.bool_: value.flat[-1]=~value.flat[-1]
    elif value.dtype==np.int64: value.flat[-1]=999
    else: value.flat[-1]+=.1
    with pytest.raises(AssertionError): p.checker().check_life(raw,meta,SHORT,SHORT_PARENT)


@pytest.mark.parametrize('field',['index','life','config','tag','qualification','arms','founder_rng',
    'training_rng','branch_rng','copy_rng','theta_writable','exact_alias_branches','tissue','blueprint'])
def test_d109_parent_metadata_corruption(piece,field):
    raw,meta=piece; parent=meta['parent']
    if field=='index': parent[field]+=1
    elif field=='life': parent[field]=True
    elif field=='config': parent[field]['teaching']+=1
    elif field=='qualification': parent[field]=True
    elif field=='arms': parent[field].reverse()
    elif field=='training_rng': parent[field][0][0]='bad'
    elif field in ('branch_rng','copy_rng'): parent[field][0][0][0]='bad'
    elif field=='exact_alias_branches': parent[field]=0
    elif field in ('tissue','blueprint'): parent[field]={}
    else: parent[field]='bad'
    with pytest.raises((AssertionError,KeyError)): p.checker().check_life(raw,meta,SHORT,SHORT_PARENT)


def test_d109_parent_config_and_replay_proofs(block):
    raw,meta=deepcopy(block); meta['parent_config']['teaching']+=1
    with pytest.raises(AssertionError):
        p.checker().check_block(raw,meta,SHORT,replay=False,parent_cfg=SHORT_PARENT)
    raw,meta=deepcopy(block); meta['lives'][0]['replay']['parent_replay']['full_life_replay']=False
    with pytest.raises(AssertionError):
        p.checker().check_block(raw,meta,SHORT,replay=False,parent_cfg=SHORT_PARENT)
    raw,meta=deepcopy(block); meta['lives'][0]['replay']['parent_replay']['max_abs']=1.
    with pytest.raises(AssertionError):
        p.checker().check_block(raw,meta,SHORT,replay=False,parent_cfg=SHORT_PARENT)


def test_d109_new_estimate_does_not_pool_old_outcomes():
    result=p.summarize(synthetic(),SHORT)
    assert result['tissues']==list(range(55000,55008)) and result['source_tissues']==list(range(54000,54008))
    assert result['source_records_previously_observed'] is False
    assert result['fresh_physical_tissue_parameters'] is True
    assert len(result['primary']['block_means'])==8
    assert set(p.TISSUES).isdisjoint(p.base.TISSUES) and set(p.SOURCE_TISSUES).isdisjoint(p.base.SOURCE_TISSUES)
