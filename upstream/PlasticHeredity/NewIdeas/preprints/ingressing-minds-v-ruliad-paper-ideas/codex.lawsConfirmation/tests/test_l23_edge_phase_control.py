import ast
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from laws_confirmation import l23_edge_phase_control as s
from laws_confirmation.io import sha256_file


@pytest.fixture(scope='module')
def check():
    return s.checker()


@pytest.fixture(scope='module')
def ctx():
    return s.source.old.context(s.DISPOSABLE, s.source.old.Config(draws=2, sweeps=6, times=(0, 1, 2, 3, 6)))


@pytest.fixture(scope='module')
def inst(ctx):
    return s.source.instruments(ctx)


@pytest.mark.parametrize('phase', range(4))
def test_edges_matched_degree_orientation_topology_and_coordinates(check, phase):
    edges = s.selected_edges(phase)
    np.testing.assert_array_equal(edges, check.expected_edges(phase))
    np.testing.assert_array_equal(edges, np.roll(s.selected_edges(0), (phase, phase), axis=(1, 2)))
    assert edges.dtype == bool and edges.sum() == 128
    np.testing.assert_array_equal(edges.sum(axis=(1, 2)), [64, 64])
    degree = sum(edges[a].astype(int)+np.roll(edges[a], 1, a) for a in (0, 1))
    np.testing.assert_array_equal(np.bincount(degree.ravel()), [64, 128, 64])
    if phase:
        assert not (edges & s.selected_edges(0)).any()


@pytest.mark.parametrize('phase', range(4))
@pytest.mark.parametrize('removal', [.5, 1.])
def test_shared_diffusion_matches_independent_flux_and_conserves(check, phase, removal):
    v = np.random.default_rng(8560).normal(size=(2, 3, 16, 16))
    edges = s.selected_edges(phase)
    actual = s.old.diffusion(v, edges, removal)
    weights = 1.-removal*edges
    np.testing.assert_allclose(actual, check.previous.weighted_laplacian(v, weights), rtol=0, atol=2e-15)
    np.testing.assert_allclose(actual.sum(axis=(-2, -1)), 0, rtol=0, atol=2e-14)
    np.testing.assert_array_equal(s.old.diffusion(np.ones_like(v), edges, removal), 0)
    energy = sum((weights[a]*np.square(np.roll(v, -1, a-2)-v)).sum(axis=(-2, -1)) for a in (0, 1))/4
    np.testing.assert_allclose((v*actual).sum(axis=(-2, -1)), -energy, rtol=0, atol=1e-12)


@pytest.mark.parametrize('norm', range(2))
@pytest.mark.parametrize('phase,removal,source_arm', [(0,.5,1),(0,1.,3),(2,.5,2),(2,1.,4)])
def test_all_known_source_phases_are_stream_exact(ctx, inst, norm, phase, removal, source_arm):
    a, da = s.simulate(ctx, inst, norm, phase, removal)
    b, db = s.old.simulate(ctx, inst, 2, norm, source_arm)
    assert set(a) == set(b) and da == db
    for key in a:
        np.testing.assert_array_equal(a[key], b[key])


@pytest.mark.parametrize('phase', range(4))
@pytest.mark.parametrize('removal', [.5, 1.])
def test_all_phase_replays_and_observers(ctx, inst, check, phase, removal):
    row, compact, record = s.execute_panel(ctx, inst, 0, phase, removal, check)
    assert record['replay_max_abs'] <= 1e-10 and record['source_arm'] is None
    assert row['values'].shape == (5,12,3,8,2,2,3,4)
    assert compact['final_V'].shape == (252,2,16,16)


@pytest.mark.parametrize('key', ['theta','case_ids','offsets','birth_noise','s2_V','s6_ema','s6_R',
                                 'max_mean_drift','max_clip_fraction','rng','phase','removal'])
def test_corruption_rejected(ctx, inst, check, key):
    raw, digest = s.simulate(ctx, inst, 0, 1, .5)
    phase, removal = 1, .5
    if key == 'rng': digest = 'wrong'
    elif key == 'phase': phase = 3
    elif key == 'removal': removal = 1.
    else: raw[key].flat[0] += 1
    with pytest.raises(AssertionError):
        check.check_replay(raw, inst, ctx, 0, phase, removal, digest)


def test_birth_instructions_and_random_stream_not_phase_conditioned(ctx, inst):
    cases = [s.simulate(ctx, inst, 1, p, r) for p in range(4) for r in (.5, 1.)]
    assert len({digest for _, digest in cases}) == 1
    for raw, _ in cases[1:]:
        for key in ('theta','case_ids','offsets','birth_noise','s0_V','s0_ema','s0_R'):
            np.testing.assert_array_equal(raw[key], cases[0][0][key])
    with pytest.raises(ValueError): s.selected_edges(4)
    with pytest.raises(ValueError): s.simulate(ctx, inst, 0, 1, .25)


def blank_arrays(draws=2):
    shape = (2,4,5,12,3,8,draws,2,3,4)
    _, _, distance, _, counts = s.checker().previous.seam_check.geometry(np.zeros((4,16,16)),2)
    fresh = dict(values=np.zeros(shape), active=np.ones(shape[:-2]+(2,),dtype=np.uint8),
        metrics=np.zeros((2,4,12,3,8,draws,6)), final_V=np.zeros((2,4,252,draws,16,16)),
        diagnostics=np.zeros((2,4,252,draws,2)), edges=np.stack([s.selected_edges(p) for p in range(4)]),
        counts=counts[:,:3], distance=distance)
    previous = {}
    for key in ('values','active','metrics','diagnostics'):
        a = fresh[key]
        previous[key] = np.zeros((2,5,*a.shape[2:]), dtype=a.dtype)
        if key == 'active': previous[key][:] = 1
    previous.update(counts=fresh['counts'], distance=fresh['distance'])
    return fresh, previous


@pytest.fixture(scope='module')
def complete_short(ctx, inst, check):
    fresh, previous = blank_arrays()
    source_panels, anchors = [], []
    for n in range(2):
        for arm in range(5):
            raw, digest = s.old.simulate(ctx, inst, 2, n, arm)
            row = s.old.observe(raw, inst, 2, ctx['config'], check.previous)
            for key in ('values','active','metrics'): previous[key][n,arm] = row[key]
            previous['diagnostics'][n,arm] = np.stack((raw['max_mean_drift'],raw['max_clip_fraction']),axis=-1)
            source_panels.append(dict(geometry=2,norm=n,arm=arm,rng_final=digest,
                state_sha256={f's{t}_{k}':s.source.base.array_digest(raw[f's{t}_{k}'])
                              for t in ctx['config'].times for k in ('V','ema','R')}))
        for i,(_,phase,removal) in enumerate(s.NEW):
            row, compact, _ = s.execute_panel(ctx,inst,n,phase,removal,check)
            for key in ('values','active','metrics'): fresh[key][n,i] = row[key]
            fresh['diagnostics'][n,i] = compact['diagnostics']; fresh['final_V'][n,i] = compact['final_V']
        for phase,removal,arm in s.ANCHORS:
            row,compact,record = s.execute_panel(ctx,inst,n,phase,removal,check)
            anchors.append((row,compact,record,arm))
    source_record = dict(panels=source_panels)
    for row,compact,record,arm in anchors:
        assert check.check_anchor(row,compact,record,previous,source_record,arm)
    return fresh,previous,source_record,anchors


def test_complete_factorial_source_assembly_and_persistence(complete_short,check,tmp_path):
    fresh,previous,_,_ = complete_short
    combined = s.assemble(previous,fresh)
    assert check.check_block(fresh,previous,combined)
    s.source.base.atomic_npz(tmp_path/'new_only.npz',fresh,tmp_path)
    with np.load(tmp_path/'new_only.npz',allow_pickle=False) as f:
        saved = dict(f)
        for key in fresh: np.testing.assert_array_equal(saved[key],fresh[key])
        assert check.check_block(saved,previous,s.assemble(previous,saved))


@pytest.mark.parametrize('kind',['hash','rng','values','diagnostics','source_arm'])
def test_anchor_corruption_rejected(complete_short,check,kind):
    fresh,previous,source_record,anchors = complete_short
    row,compact,record,arm = deepcopy(anchors[0])
    if kind == 'hash': record['state_sha256']['s6_V'] = 'wrong'
    elif kind == 'rng': record['rng_final'] = 'wrong'
    elif kind == 'values': row['values'].flat[0] += 1
    elif kind == 'diagnostics': compact['diagnostics'].flat[0] += 1
    else: arm = 4
    with pytest.raises(AssertionError): check.check_anchor(row,compact,record,previous,source_record,arm)


@pytest.mark.parametrize('key',['values','active','metrics','diagnostics'])
def test_source_assembly_corruption_rejected(check,key):
    fresh,previous = blank_arrays()
    combined = s.assemble(previous,fresh)
    combined[key].flat[0] += 1
    with pytest.raises(AssertionError): check.check_block(fresh,previous,combined)


@pytest.fixture(scope='module')
def blocks():
    shape = (2,9,5,12,3,8,2,2,3,4)
    blocks = []
    for b in range(3):
        x = np.full(shape,(b+1)/1e6)
        for axis,size in enumerate(shape):
            weights = np.arange(1,size+1,dtype=float)
            if axis == 5: weights = np.array([1,1,1,1,.6,1,.2,.37])
            dims=[1]*len(shape);dims[axis]=size
            x *= weights.reshape(dims)
        blocks.append(x)
    metrics = [np.random.default_rng(b).normal(size=(2,9,12,3,8,2,6)) for b in range(3)]
    return blocks,metrics


def test_focal_axes_and_source_only_flags(blocks,check):
    x,m=blocks
    summary,focal=s.summary_of(x,m),s.focal_of(x)
    assert check.check_summary(x,m,summary,focal)
    gain=2*5*6.5*2*1.5*1.5/1e6
    assert focal[0]['mean'] == pytest.approx(gain)
    assert focal[1]['mean'] == pytest.approx(.63*gain)
    assert focal[2]['mean'] == pytest.approx(2*gain) and focal[2]['source_only']
    assert focal[4]['mean'] == pytest.approx(3*gain)
    assert focal[12]['mean'] == pytest.approx(2*gain)
    assert sum(f['source_only'] for f in focal) == 8


@pytest.mark.parametrize('kind',['mean','block','pair','count','phase','source_only','missing','summary','cost','metrics'])
def test_pooled_corruption_rejected(blocks,check,kind):
    x,m=blocks
    summary,focal=s.summary_of(x,m),s.focal_of(x)
    if kind == 'mean': focal[0]['mean'] += .01
    elif kind == 'block': focal[0]['block_means'][0] += .01
    elif kind == 'pair': focal[0]['pair_means'][0] += .01
    elif kind == 'count': focal[0]['positive'] += 1
    elif kind == 'phase': focal[0]['phase']=2
    elif kind == 'source_only': focal[0]['source_only']=True
    elif kind == 'missing': focal.pop()
    else: summary[{'summary':'means','cost':'composition_block_means','metrics':'metric_means'}[kind]].flat[0] += .01
    with pytest.raises(AssertionError):check.check_summary(x,m,summary,focal)


def test_contract_lives_storage_and_no_new_physics():
    c=s.contract()
    assert c == json.loads(json.dumps(c))
    assert c['new_intervention_lives'] == 16*2*4*252*8
    assert c['source_anchor_lives'] == 16*2*2*252*8
    assert c['independent_replay_lives'] == c['new_intervention_lives']+c['source_anchor_lives']
    fresh,_=blank_arrays(draws=8)
    assert 16*sum(a.nbytes for a in fresh.values())+200*1024**2 < s.ALLOWANCE
    assert c['diagonal_phases_only'] and c['unchanged_d084_step'] and c['hereditary_boundaries'] == 0
    assert not c['duplicated_source_block_statistics'] and not c['duplicated_source_states']


@pytest.mark.parametrize('kind',['intact','index','config','count','axes','rng','bridge','state'])
def test_source_record_metadata_checked(check,kind):
    cfg=s.asdict(s.source.CONFIG)
    record=dict(tissue=402088,passes=True,config=deepcopy(cfg),independently_checked_panels=30,
        source_bridge_panels=6,panels=[dict(geometry=g,norm=n,arm=a,rng_final='same',
            replay_max_abs=0.,source_bridge=a==0,state_sha256={f's{t}_{k}':'hash'
                for t in cfg['times'] for k in ('V','ema','R')})
            for g in range(3) for n in range(2) for a in range(5)])
    if kind=='intact':
        assert check.check_source_record(record,402088,cfg)
        return
    if kind=='index':record['tissue']+=1
    elif kind=='config':record['config']['draws']+=1
    elif kind=='count':record['source_bridge_panels']-=1
    elif kind=='axes':record['panels'].reverse()
    elif kind=='rng':record['panels'][0]['rng_final']='wrong'
    elif kind=='bridge':record['panels'][0]['source_bridge']=False
    else:record['panels'][0]['state_sha256'].pop('s0_R')
    with pytest.raises(AssertionError):check.check_source_record(record,402088,cfg)


@pytest.fixture
def frozen(tmp_path,monkeypatch):
    (tmp_path/'tmp').mkdir();(tmp_path/'logs').mkdir()
    p=tmp_path/'source.json';s.strict_json(p,{'synthetic':True},tmp_path)
    directory=tmp_path/'tmp'/f'{s.RUN_ID}_benchmark';directory.mkdir()
    for name in ('panels.npz','verification.json'):s.strict_json(directory/name,{'synthetic':True},tmp_path)
    monkeypatch.setattr(s,'input_paths',lambda root:[p])
    monkeypatch.setattr(s,'source_verified',lambda root,hashes:True)
    monkeypatch.setattr(s,'preflight',lambda root,**kw:[0,1,2,3])
    timing=dict(run_id=s.RUN_ID,passed=True,effects_not_reported=True,disposable=s.DISPOSABLE,norm=0,
        benchmark_panels=6,config=s.asdict(s.source.CONFIG),arm_seconds=[4.]*6,write_seconds=6.,
        panel_seconds=5.,hash_seconds=1.,projected_seconds=1142.,must_detach=True,
        input_sha256={str(p):sha256_file(p)},benchmark_files={str(f):sha256_file(f) for f in directory.iterdir()})
    s.strict_json(s.timing_path(tmp_path),timing,tmp_path)
    return tmp_path,p


@pytest.mark.parametrize('kind',['panels','config','norm','arm','estimate','forecast','detach','artifacts'])
def test_bad_benchmark_refused_before_preparation(frozen,kind):
    root,_=frozen
    path=s.timing_path(root);timing=json.loads(path.read_text())
    if kind=='panels':timing['benchmark_panels']=5
    elif kind=='config':timing['config']['sweeps']=299
    elif kind=='norm':timing['norm']=1
    elif kind=='arm':timing['arm_seconds'][0]=0.
    elif kind=='estimate':timing['panel_seconds']+=1.
    elif kind=='forecast':timing['projected_seconds']-=1.
    elif kind=='detach':timing['must_detach']=False
    else:timing['benchmark_files'].pop(next(iter(timing['benchmark_files'])))
    s.strict_json(path,timing,root)
    with pytest.raises(AssertionError):s.prepare(root)
    assert not (root/'runs'/s.RUN_ID).exists() and not (root/'outputs'/s.RUN_ID).exists()


def test_freeze_integrity_and_no_overwrite(frozen):
    root,p=frozen
    manifest=s.prepare(root)
    assert s.verify(root)==manifest
    with pytest.raises(FileExistsError):s.prepare(root)
    s.strict_json(p,{'changed':True},root)
    with pytest.raises(AssertionError):s.verify(root)


@pytest.mark.parametrize('kind',['contract','status','timing','rows','benchmark'])
def test_manifest_corruption_rejected(frozen,kind):
    root,_=frozen;s.prepare(root)
    if kind=='rows':s.strict_json(root/'outputs'/s.RUN_ID/'input_hashes.sha256',{'wrong':True},root)
    elif kind=='benchmark':s.strict_json(root/'tmp'/f'{s.RUN_ID}_benchmark'/'verification.json',{'wrong':True},root)
    else:
        path=root/'runs'/s.RUN_ID/('STATUS.json' if kind=='status' else 'MANIFEST.json')
        data=json.loads(path.read_text())
        if kind=='contract':data['phases']=[0,2]
        elif kind=='status':data['status']='COMPLETE'
        else:data['timing']['projected_seconds']=0
        s.strict_json(path,data,root)
    with pytest.raises(AssertionError):s.verify(root)


def test_detach_never_polls_and_long_run_requires_detachment(frozen,monkeypatch):
    root,_=frozen;s.prepare(root)
    with pytest.raises(RuntimeError,match='detached execution required'):s.run_experiment(root)
    calls=[]
    def popen(args,**kwargs):
        calls.append((args,kwargs));return SimpleNamespace(pid=12345)
    monkeypatch.setattr(s.subprocess,'Popen',popen)
    record=s.detach(root)
    assert record['pid']==12345 and record['polling_owner']=='user'
    assert calls[0][1]['start_new_session'] is True and calls[0][0][-1]=='--run'
    with pytest.raises(FileExistsError):s.detach(root)
    assert len(calls)==1


def test_external_reserve_and_independent_checker(monkeypatch,tmp_path):
    monkeypatch.setattr(s.source,'preflight',lambda root:[0,1,2,3])
    monkeypatch.setattr(s.shutil,'disk_usage',lambda root:SimpleNamespace(free=s.RESERVE+s.ALLOWANCE-1))
    with pytest.raises(RuntimeError):s.preflight(tmp_path)
    assert s.preflight(tmp_path,starting=False)==[0,1,2,3]
    tree=ast.parse((Path(__file__).resolve().parents[1]/s.SCIENCE[1]).read_text())
    for node in ast.walk(tree):
        if isinstance(node,ast.Attribute):assert node.attr not in ('simulate','step','selected_edges','assemble','summary_of','focal_of')
