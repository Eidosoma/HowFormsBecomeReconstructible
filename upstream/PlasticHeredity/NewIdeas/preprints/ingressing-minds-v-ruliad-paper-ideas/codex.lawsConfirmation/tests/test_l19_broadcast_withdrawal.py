"""D101 short disposable tests only; fresh main seeds never simulated here."""
from copy import deepcopy
from dataclasses import replace
import inspect
import os
from pathlib import Path
import subprocess
import sys

import numpy as np
import pytest

from laws_confirmation import l19_broadcast_withdrawal as p
from laws_confirmation import l19_broadcast_withdrawal_run as run
from laws_confirmation.io import DEFAULT_EXTERNAL_ROOT as ROOT,canonical_digest

SHORT=replace(p.CONFIG,settle=4,training_cycles=1,cycles=4,teaching=2,free=3)


@pytest.fixture(scope='module')
def block(): return p.execute_block(p.DISPOSABLE,SHORT)


@pytest.fixture
def piece(block):
    raw,meta=deepcopy(block)
    return {k:v[0] for k,v in raw.items()},meta['lives'][0]


def test_fixed_design():
    assert p.TISSUES==tuple(range(46000,46008)) and p.DISPOSABLE not in p.TISSUES
    assert p.CONFIG==p.Config() and p.CONFIG.teaching==500 and p.CONFIG.free==1000
    assert (p.CONFIG.training_cycles,p.CONFIG.primary_cycle,p.CONFIG.rescue_cycle,p.CONFIG.cycles)==(3,3,4,6)
    assert run.contract()['absolute_fidelity_gate'] is None
    assert run.contract()['output_hash_count']==len(run.output_names())==19
    assert p.contract()['fresh_branches']==64 and p.contract()['exact_alias_branches']==16


@pytest.mark.parametrize('change',[
    dict(lives=0),dict(lives=True),dict(lives=1.5),dict(settle=-1),dict(training_cycles=0),
    dict(cycles=2),dict(primary_cycle=2),dict(rescue_cycle=3),dict(rescue_cycle=7),
    dict(teaching=0),dict(free=-1),dict(shift=0),dict(shift=16),dict(shift=True),
    dict(amplitude=0),dict(amplitude=3),dict(amplitude=float('nan')),dict(amplitude=float('inf')),
    dict(amp_threshold=0),dict(amp_threshold=1.2),dict(amp_threshold=float('nan'))])
def test_config_rejects_invalid(change):
    with pytest.raises(ValueError): replace(p.CONFIG,**change)


@pytest.mark.parametrize('identity',[-1,True,1.5,'46000'])
def test_identity_rejected(identity):
    with pytest.raises(ValueError): p.context(identity)


def test_import_from_fresh_process():
    result=subprocess.run([sys.executable,'-c',
        'from laws_confirmation.l19_broadcast_withdrawal import api; '
        'assert api()["teaching"].__name__=="teaching.pipeline"; print("imports only")'],
        cwd=p.WS,env=os.environ.copy(),capture_output=True,text=True,check=True)
    assert result.stdout.strip()=='imports only'


def test_full_disposable_replay(block):
    raw,meta=block
    assert p.checker().check_block(raw,meta,SHORT,replay=True)
    assert all(m['replay']['max_abs']==0. for m in meta['lives'])


def test_common_birth_and_rescue_alias(piece):
    raw,meta=piece
    for arm in range(4): np.testing.assert_array_equal(raw['states'][arm,0],raw['training'][-1])
    np.testing.assert_array_equal(raw['states'][1,:10],raw['states'][3,:10])
    assert not np.array_equal(raw['states'][1,-1],raw['states'][3,-1])
    assert all(d==meta['branch_rng'][0] for d in meta['branch_rng'])


def test_order_and_duplicate_aliases(piece):
    raw,meta=piece
    other,om=p.simulate_life(p.DISPOSABLE,0,SHORT,arms=('rescue','wrong','withdrawn','continued','withdrawn'))
    for i,j in enumerate((3,2,1,0,1)):
        np.testing.assert_array_equal(other['states'][i],raw['states'][j])
        assert om['branch_rng'][i]==meta['branch_rng'][j]


def test_free_window_has_no_target_argument(piece,monkeypatch):
    raw,_=piece
    assert set(inspect.signature(p.evolve).parameters)=={'state','theta','ctx','random','steps','teacher','amplitude'}
    class Poison:
        def __array__(self,*args,**kw): raise AssertionError('observer target accessed')
    teachers=p.schedule('withdrawn',Poison(),SHORT)
    assert teachers==(None,)*SHORT.cycles
    monkeypatch.setattr(p,'measure',lambda *a,**kw: (_ for _ in ()).throw(AssertionError('observer called')))
    observed,mask,_=p.branch(raw['training'][-1],raw['theta'],p.context(p.DISPOSABLE),
        p.DISPOSABLE,0,teachers,SHORT)
    np.testing.assert_array_equal(observed,raw['states'][1])
    np.testing.assert_array_equal(mask,raw['fresh'])


def test_wrong_teacher_preserves_histogram_and_geometry(piece):
    raw,_=piece; original=raw['ancestor']; wrong=p.schedule('wrong',original,SHORT)[0]
    np.testing.assert_array_equal(wrong,np.roll(original,8,-1))
    np.testing.assert_array_equal(np.sort(wrong.ravel()),np.sort(original.ravel()))
    assert wrong.mean()==original.mean() and (wrong*wrong).sum()==(original*original).sum()
    for axis in (0,1):
        assert np.count_nonzero(wrong!=np.roll(wrong,1,axis))==np.count_nonzero(original!=np.roll(original,1,axis))


def test_different_observer_cannot_change_withdrawn_body(piece):
    raw,_=piece; ctx=p.context(p.DISPOSABLE)
    a=p.branch(raw['training'][-1],raw['theta'],ctx,p.DISPOSABLE,0,p.schedule('withdrawn',raw['ancestor'],SHORT),SHORT)
    b=p.branch(raw['training'][-1],raw['theta'],ctx,p.DISPOSABLE,0,p.schedule('withdrawn',-raw['ancestor'],SHORT),SHORT)
    np.testing.assert_array_equal(a[0],b[0]); assert a[2]==b[2]


def test_equal_time_noise_consumption(piece):
    raw,meta=piece; ctx=p.context(p.DISPOSABLE)
    r=p.rng(p.DISPOSABLE,0,'branch:1')
    r.integers(0,2,1); r.integers(0,2,1)
    for _ in range(1+SHORT.teaching+SHORT.free): r.standard_normal((1,16,16))
    assert all(meta['branch_rng'][i][0]==canonical_digest(r.bit_generator.state) for i in range(4))
    shorter=replace(SHORT,teaching=1)
    observed,_,digests=p.branch(raw['training'][-1],raw['theta'],ctx,p.DISPOSABLE,0,(None,)*4,shorter)
    assert digests[0]!=meta['branch_rng'][1][0]
    assert not np.array_equal(observed,raw['states'][1])


def test_regrowth_counts_do_not_include_training(piece):
    raw,_=piece
    assert np.all(raw['values'][:,0,13]==0) and np.all(raw['values'][:,1,13]==0)
    count=(raw['fresh'][:3].sum(axis=0)>=2).sum()
    assert count>=64 and np.all(raw['values'][:,3,13]==count)
    assert np.all(raw['fresh'].sum(axis=(1,2))==128)


@pytest.mark.parametrize('field',['theta','ancestor','training','states','values'])
def test_float_corruption_rejected(piece,field):
    raw,meta=piece; raw[field].flat[-1]+=.1
    with pytest.raises(AssertionError): p.checker().check_life(raw,meta,SHORT)


@pytest.mark.parametrize('field',['fresh','training_fresh'])
def test_mask_corruption_rejected(piece,field):
    raw,meta=piece; raw[field].flat[-1]=~raw[field].flat[-1]
    with pytest.raises(AssertionError): p.checker().check_life(raw,meta,SHORT)


@pytest.mark.parametrize('field',['index','life','config','arms','founder_rng','training_rng','branch_rng','theta_writable'])
def test_metadata_corruption_rejected(piece,field):
    raw,meta=piece
    if field=='index': meta[field]+=1
    elif field=='life': meta[field]=True
    elif field=='config': meta[field]['teaching']+=1
    elif field=='arms': meta[field].reverse()
    elif field=='founder_rng': meta[field]='bad'
    elif field=='training_rng': meta[field][0]='bad'
    elif field=='branch_rng': meta[field][0][0]='bad'
    else: meta[field]=True
    with pytest.raises(AssertionError): p.checker().check_life(raw,meta,SHORT)


@pytest.mark.parametrize('shape',[(16,),(4,4),(1,16,16)])
def test_teacher_broadcast_is_rejected(piece,shape):
    raw,_=piece
    with pytest.raises(ValueError):
        p.evolve(raw['training'][-1],raw['theta'],p.context(p.DISPOSABLE),p.rng(1,0,'test'),1,np.ones(shape))


def test_observer_rejects_patch_target(piece):
    raw,_=piece
    with pytest.raises(ValueError): p.measure(raw['states'],raw['ancestor'].ravel()[:16],raw['fresh'],SHORT)


def test_weak_correct_sign_is_not_qualified_fidelity(piece):
    raw,_=piece
    raw['states'][:,:,0]=.1*raw['ancestor']
    values=p.measure(raw['states'],raw['ancestor'],raw['fresh'],SHORT)
    assert np.all(values[:,:,0]==0) and np.all(values[:,:,12]==0)
    assert np.all(values[:,:,10]==0)


def test_hand_built_primary(block):
    blocks=[deepcopy(block[0]) for _ in range(8)]
    for b in blocks:
        b['values'].fill(0)
        b['values'][:,:,3:,13]=64
        b['values'][:,0,3:,12]=48
        b['values'][:,1,3:,12]=16
    summary=p.summarize(blocks,SHORT)
    assert summary['primary']['mean']==.5
    assert summary['primary']['pointwise_block_bootstrap_95']==[.5,.5]
    assert summary['label']=='CONTINUED_BROADCAST_ADVANTAGE'
    assert summary['trajectories'][0]['regrown'] is None


def test_negative_primary_is_not_certified(block):
    blocks=[deepcopy(block[0]) for _ in range(8)]
    for b in blocks:
        b['values'].fill(0); b['values'][:,:,3:,13]=64
        b['values'][:,1,3:,12]=32
    assert p.summarize(blocks,SHORT)['label']=='NO_QUALIFIED_CONTINUED_ADVANTAGE'


def test_summary_and_independent_pooling(block):
    blocks=[block[0]]*8
    assert p.checker().check_summary(p.summarize(blocks,SHORT),blocks,SHORT)


@pytest.mark.parametrize('kind',['mean','interval','label','observer','count','training','gate','missing'])
def test_summary_corruption_rejected(block,kind):
    blocks=[block[0]]*8; result=p.summarize(blocks,SHORT)
    if kind=='mean': result['primary']['mean']+=.01
    elif kind=='interval': result['primary']['pointwise_block_bootstrap_95'][0]-=.1
    elif kind=='label': result['label']='made_up'
    elif kind=='observer': result['primary']['observer']='whole'
    elif kind=='count': result['trajectories'][0]['regrown_denominators'][0][0]=1
    elif kind=='training': result['training_specificity']['mean']+=.01
    elif kind=='gate': result['absolute_fidelity_gate']=.8
    else: result.pop('target_disagreement')
    with pytest.raises(AssertionError): p.checker().check_summary(result,blocks,SHORT)


@pytest.mark.parametrize('defect',['empty','unpaired','missing_block','nan'])
def test_invalid_pool_rejected(block,defect):
    blocks=[deepcopy(block[0]) for _ in range(8)]
    if defect=='empty': blocks[0]['values'][0,0,3,13]=0
    elif defect=='unpaired': blocks[0]['values'][0,0,3,13]+=1
    elif defect=='missing_block': blocks.pop()
    else: blocks[0]['values'].flat[0]=np.nan
    with pytest.raises(ValueError): p.summarize(blocks,SHORT)


def test_short_source_replay():
    a=p.api(); cfg=replace(a['TeachConfig'](),futures=2,cycles=3,settle_sweeps=3,render_sweeps=4,free_sweeps=3)
    raw,meta=p.source_control(p.DISPOSABLE,cfg)
    assert meta['replay']['full_source_replay'] and meta['replay']['max_abs']==0
    assert p.checker().check_source(raw,meta)['metrics_pass']


def test_source_wrappers_restored_on_failure(monkeypatch):
    old=p.api()['teaching']; before=(old._free,old.fission_with_mask)
    def fail(*args,**kw): raise RuntimeError('injected')
    monkeypatch.setattr(old,'teach_lineage',fail)
    with pytest.raises(RuntimeError,match='injected'): p.source_control(p.DISPOSABLE)
    assert before==(old._free,old.fission_with_mask)


def test_documentation_exception_is_exact(monkeypatch):
    case=run.LEGACY_CASE
    run.check_legacy_row(case['historical_sha256'],case['path'])
    with pytest.raises(AssertionError): run.check_legacy_row('0'*64,case['path'])
    monkeypatch.setattr(run,'sha256_file',lambda path:'0'*64)
    with pytest.raises(AssertionError): run.check_legacy_row(case['historical_sha256'],case['path'])


def test_other_historical_drift_rejected(tmp_path):
    target=tmp_path/'source.txt'
    run.u.write_json(target,{'fixture':True},ROOT)
    with pytest.raises(AssertionError): run.check_legacy_row('0'*64,str(target))


def test_saved_roundtrip_and_external_guard(block,tmp_path):
    raw,meta=block
    loaded=run.u.save_pair(tmp_path,'block',raw,meta,ROOT)
    assert p.checker().check_block(loaded,run.u.read_json(tmp_path/'block.json'),SHORT,replay=False)
    with pytest.raises(FileExistsError): run.u.write_json(tmp_path/'block.json',{},ROOT)
    with pytest.raises(ValueError): run.u.write_npz(p.WS/'forbidden.npz',raw,ROOT)
    with pytest.raises(ValueError): run.u.write_json(p.WS/'forbidden.json',{},ROOT)


def test_duplicate_json_rejected(tmp_path):
    # A corruption fixture is a generated test artifact, not a source edit.
    path=tmp_path/'duplicate.json'
    with path.open('x') as handle: handle.write('{"a":1,"a":2}')
    with pytest.raises(ValueError,match='duplicate'): run.u.read_json(path)


def test_missing_detached_launch_rejected(tmp_path):
    with pytest.raises(FileNotFoundError): run.detached_guard(tmp_path,True)


def test_run_already_reserved_blocks_prepare(monkeypatch,tmp_path):
    monkeypatch.setattr(run.u,'preflight',lambda *a,**kw:None)
    monkeypatch.setattr(run,'main_inputs',lambda root:{})
    monkeypatch.setattr(run,'timing_checked',lambda root:{})
    (tmp_path/'runs'/p.RUN_ID).mkdir(parents=True)
    with pytest.raises(FileExistsError): run.prepare(tmp_path)
    assert not (tmp_path/'outputs'/p.RUN_ID).exists()


def test_frozen_input_drift_rejected(monkeypatch,tmp_path):
    record=dict(test_proof={'path':str(tmp_path/'proof.xml')},contract=run.contract(),
        main_futures_seen=0,environment=run.environment_manifest(),input_sha256={'x':'old'})
    monkeypatch.setattr(run.u,'read_json',lambda path:record)
    monkeypatch.setattr(run,'test_proof',lambda *args:record['test_proof'])
    monkeypatch.setattr(run,'science_paths',lambda root:[])
    monkeypatch.setattr(run,'source_artifacts',lambda *args:[])
    monkeypatch.setattr(run.u,'hashes',lambda paths:{'x':'new'})
    with pytest.raises(AssertionError): run.frozen(tmp_path)
